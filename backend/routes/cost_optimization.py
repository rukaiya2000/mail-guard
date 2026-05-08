"""Cost optimization: reduce API costs through intelligent model selection and caching."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

from database import get_db, User, ClassificationLog
from auth import get_optional_user
from prompts import get_model_config, MODEL_CONFIG
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["cost"])


class ModelCostMetrics(BaseModel):
    """Cost and performance metrics for a model."""
    model: str
    accuracy_percentage: float
    cost_per_classification: float
    total_cost_period: float
    latency_ms: float
    cost_efficiency_score: float  # accuracy / cost (higher is better)


class CostOptimizationPlan(BaseModel):
    """Recommended cost optimization strategy."""
    current_monthly_cost: float
    optimized_monthly_cost: float
    savings_percent: float
    recommendations: list[str]
    models_ranking: list[dict]


class CachingStrategy(BaseModel):
    """Caching analysis and recommendations."""
    duplicate_classifications: int
    total_classifications: int
    cache_hit_rate: float
    potential_savings: float
    recommendation: str


def calculate_cost_per_classification(model: str, avg_tokens: int = 500) -> float:
    """Calculate average cost per classification for a model."""
    config = get_model_config(model)
    # Estimate: 70% prompt tokens, 30% completion tokens
    prompt_tokens = int(avg_tokens * 0.7)
    completion_tokens = int(avg_tokens * 0.3)

    prompt_cost = (prompt_tokens / 1000) * config["prompt_cost_per_1k_tokens"]
    completion_cost = (completion_tokens / 1000) * config["completion_cost_per_1k_tokens"]

    return prompt_cost + completion_cost


def calculate_cost_efficiency_score(accuracy: float, cost: float) -> float:
    """Calculate cost efficiency: accuracy per dollar spent.

    Higher is better (more accuracy for less money).
    """
    if cost == 0:
        return 0
    return (accuracy / 100) / cost


@router.get("/cost/analysis")
def get_cost_analysis(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get detailed cost analysis by model."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_date,
        ClassificationLog.success == True
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if not classifications:
        return {"error": "No data available", "status": "no_data"}

    # Group by model
    model_stats = {}
    for model_name in MODEL_CONFIG.keys():
        model_classifications = [c for c in classifications if c.model == model_name]

        if model_classifications:
            total = len(model_classifications)
            avg_tokens = sum(c.tokens_used for c in model_classifications) / total

            # Calculate cost
            config = get_model_config(model_name)
            total_cost = sum(
                (c.tokens_used / 1000) * (
                    config["prompt_cost_per_1k_tokens"] * 0.7 +
                    config["completion_cost_per_1k_tokens"] * 0.3
                )
                for c in model_classifications
            )

            # Calculate accuracy from feedback (if available)
            from database import ClassificationFeedback
            feedbacks = db.query(ClassificationFeedback).filter(
                ClassificationFeedback.created_at >= cutoff_date
            ).all()

            feedback_map = {f.classification_id: f for f in feedbacks}
            correct = sum(1 for c in model_classifications if feedback_map.get(c.id) and feedback_map.get(c.id).is_correct)
            feedback_count = sum(1 for c in model_classifications if feedback_map.get(c.id) and feedback_map.get(c.id).is_correct is not None)

            accuracy = (correct / feedback_count * 100) if feedback_count > 0 else 0

            avg_latency = sum(c.latency_ms for c in model_classifications) / total

            cost_per_class = total_cost / total if total > 0 else 0
            efficiency = calculate_cost_efficiency_score(accuracy, cost_per_class)

            model_stats[model_name] = {
                "total_classifications": total,
                "accuracy": accuracy,
                "cost_per_classification": round(cost_per_class, 6),
                "total_cost": round(total_cost, 4),
                "latency_ms": round(avg_latency, 1),
                "efficiency_score": round(efficiency, 4)
            }

    # Rank by efficiency
    ranked = sorted(
        model_stats.items(),
        key=lambda x: x[1]["efficiency_score"],
        reverse=True
    )

    return {
        "period_days": days,
        "models": model_stats,
        "ranking": [
            {
                "rank": i + 1,
                "model": model,
                "efficiency_score": data["efficiency_score"],
                "accuracy": data["accuracy"],
                "cost_per_classification": data["cost_per_classification"]
            }
            for i, (model, data) in enumerate(ranked)
        ],
        "recommendation": f"Most efficient: {ranked[0][0]} (score: {ranked[0][1]['efficiency_score']:.4f})"
    }


@router.get("/cost/optimization-plan")
def get_optimization_plan(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get cost optimization recommendations."""
    cost_analysis = get_cost_analysis(days=days, db=db, current_user=current_user)

    if "error" in cost_analysis:
        return cost_analysis

    # Calculate current costs
    total_current_cost = sum(
        m["total_cost"] for m in cost_analysis["models"].values()
    )

    total_classifications = sum(
        m["total_classifications"] for m in cost_analysis["models"].values()
    )

    # Optimization strategy: use cheapest model with >85% accuracy
    best_cheap_model = None
    for model, data in cost_analysis["models"].items():
        if data["accuracy"] >= 85 and (best_cheap_model is None or data["cost_per_classification"] < cost_analysis["models"][best_cheap_model]["cost_per_classification"]):
            best_cheap_model = model

    if best_cheap_model is None:
        best_cheap_model = cost_analysis["ranking"][0][1]  # Fallback to most efficient

    best_model_cost_per_class = cost_analysis["models"][best_cheap_model]["cost_per_classification"]
    potential_optimized_cost = best_model_cost_per_class * total_classifications

    savings = total_current_cost - potential_optimized_cost
    savings_percent = (savings / total_current_cost * 100) if total_current_cost > 0 else 0

    recommendations = []

    if savings_percent > 5:
        recommendations.append(
            f"Use {best_cheap_model} for all classifications. "
            f"Saves ${savings:.2f}/period ({savings_percent:.1f}%)"
        )

    # Ensemble optimization
    single_model_cost = cost_analysis["models"][cost_analysis["ranking"][0][0]]["cost_per_classification"]
    ensemble_cost = single_model_cost * 3  # 3 models
    recommendations.append(
        f"Use ensemble only for high-stakes emails (confident predictions: use single model for 90%+ confidence)"
    )

    # Caching recommendation
    recommendations.append(
        "Enable 24-hour email hash caching to avoid duplicate classifications (typical 5-10% savings)"
    )

    # Batch processing
    recommendations.append(
        "Use batch classification for non-urgent emails to improve token efficiency"
    )

    return CostOptimizationPlan(
        current_monthly_cost=round(total_current_cost, 2),
        optimized_monthly_cost=round(potential_optimized_cost, 2),
        savings_percent=round(savings_percent, 1),
        recommendations=recommendations,
        models_ranking=[
            {
                "rank": r[0],
                "model": r[1],
                "accuracy": cost_analysis["models"][r[1]]["accuracy"],
                "cost_per_classification": cost_analysis["models"][r[1]]["cost_per_classification"],
                "efficiency_score": r[2]
            }
            for r in [(i+1, m, cost_analysis["models"][m]["efficiency_score"]) for i, (m, _) in enumerate(cost_analysis["ranking"])]
        ]
    )


@router.get("/cost/caching-analysis")
def analyze_caching_potential(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Analyze potential savings from email hash caching."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_date,
        ClassificationLog.success == True
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if not classifications:
        return {"error": "No data available"}

    # Count duplicates by email hash
    hash_counts = {}
    for c in classifications:
        if c.email_hash:
            hash_counts[c.email_hash] = hash_counts.get(c.email_hash, 0) + 1

    # Find duplicates (hash appears > 1 time)
    duplicates = sum(count - 1 for count in hash_counts.values() if count > 1)
    total = len(classifications)

    cache_hit_rate = (duplicates / total * 100) if total > 0 else 0

    # Calculate potential savings
    avg_cost = 0.003  # Average cost per classification across models
    potential_savings = duplicates * avg_cost

    return CachingStrategy(
        duplicate_classifications=duplicates,
        total_classifications=total,
        cache_hit_rate=round(cache_hit_rate, 1),
        potential_savings=round(potential_savings, 2),
        recommendation=(
            f"Implement 24-hour email caching. "
            f"Currently {duplicates} duplicate classifications would be cached ({cache_hit_rate:.1f}% savings). "
            f"Potential savings: ${potential_savings:.2f}/period"
        )
    )


@router.post("/cost/model-selector")
def get_model_selection(
    accuracy_threshold: float = 85.0,
    latency_threshold_ms: Optional[int] = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Intelligent model selection based on constraints."""
    cost_analysis = get_cost_analysis(days=days, db=db, current_user=current_user)

    if "error" in cost_analysis:
        return cost_analysis

    # Filter models by accuracy threshold
    candidates = {
        m: data for m, data in cost_analysis["models"].items()
        if data["accuracy"] >= accuracy_threshold
    }

    if not candidates:
        return {
            "error": f"No models meet accuracy threshold of {accuracy_threshold}%",
            "suggestion": "Lower accuracy threshold or use ensemble"
        }

    # Filter by latency if specified
    if latency_threshold_ms:
        candidates = {
            m: data for m, data in candidates.items()
            if data["latency_ms"] <= latency_threshold_ms
        }

    if not candidates:
        return {
            "error": f"No models meet latency threshold of {latency_threshold_ms}ms",
            "suggestion": "Increase latency threshold or use different model"
        }

    # Rank by cost
    ranked = sorted(
        candidates.items(),
        key=lambda x: x[1]["cost_per_classification"]
    )

    return {
        "criteria": {
            "accuracy_threshold": accuracy_threshold,
            "latency_threshold_ms": latency_threshold_ms
        },
        "candidates": len(candidates),
        "recommended_model": ranked[0][0],
        "recommended_model_metrics": ranked[0][1],
        "alternatives": [
            {"model": m, "metrics": data}
            for m, data in ranked[1:3]  # Top 2 alternatives
        ]
    }


@router.get("/cost/monthly-projection")
def project_monthly_cost(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Project monthly costs based on current usage."""
    cost_analysis = get_cost_analysis(days=days, db=db, current_user=current_user)

    if "error" in cost_analysis:
        return cost_analysis

    total_cost = sum(m["total_cost"] for m in cost_analysis["models"].values())
    daily_cost = total_cost / days if days > 0 else 0
    monthly_cost = daily_cost * 30

    return {
        "period_analyzed": f"{days} days",
        "total_cost_period": round(total_cost, 2),
        "daily_average_cost": round(daily_cost, 4),
        "projected_monthly_cost": round(monthly_cost, 2),
        "projected_annual_cost": round(monthly_cost * 12, 2),
        "cost_per_classification": round(total_cost / sum(m["total_classifications"] for m in cost_analysis["models"].values()), 6) if cost_analysis["models"] else 0
    }
