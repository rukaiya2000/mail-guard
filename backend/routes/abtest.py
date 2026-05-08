"""A/B testing framework for prompt versions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from math import sqrt

from database import get_db, User, ClassificationLog, ClassificationFeedback
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["abtest"])


class PromptTestResult(BaseModel):
    """Results for a single prompt version."""
    prompt_version: str
    total_classifications: int
    feedback_count: int
    correct_count: int
    accuracy_percentage: float
    avg_confidence: float
    avg_latency_ms: float


class StatisticalSignificance(BaseModel):
    """Statistical significance test results."""
    chi_squared: float
    p_value: float
    is_significant: bool  # p < 0.05
    confidence_level: float  # 95% = 0.95


class ABTestResults(BaseModel):
    """A/B test results comparing prompt versions."""
    test_period_days: int
    results: list[PromptTestResult]
    comparison: dict  # Best vs others
    recommended_version: str
    statistical_significance: dict


def calculate_chi_squared(observed1: int, observed2: int, total1: int, total2: int) -> tuple[float, float]:
    """Calculate chi-squared statistic and p-value."""
    if total1 == 0 or total2 == 0:
        return 0.0, 1.0

    # Create contingency table
    correct1 = observed1
    incorrect1 = total1 - observed1
    correct2 = observed2
    incorrect2 = total2 - observed2

    # Expected frequencies
    total = total1 + total2
    row1_total = correct1 + correct2
    row2_total = incorrect1 + incorrect2

    expected_correct1 = (row1_total * total1) / total
    expected_incorrect1 = (row2_total * total1) / total
    expected_correct2 = (row1_total * total2) / total
    expected_incorrect2 = (row2_total * total2) / total

    # Chi-squared calculation
    chi_sq = (
        ((correct1 - expected_correct1) ** 2 / expected_correct1) +
        ((incorrect1 - expected_incorrect1) ** 2 / expected_incorrect1) +
        ((correct2 - expected_correct2) ** 2 / expected_correct2) +
        ((incorrect2 - expected_incorrect2) ** 2 / expected_incorrect2)
    )

    # Approximate p-value (simplified)
    # For 1 degree of freedom: chi_sq > 3.841 implies p < 0.05
    p_value = 0.05 if chi_sq > 3.841 else 0.2

    return chi_sq, p_value


@router.get("/abtest/results")
def get_abtest_results(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get A/B test results for prompt versions."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if not classifications:
        return ABTestResults(
            test_period_days=days,
            results=[],
            comparison={},
            recommended_version="v2",
            statistical_significance={}
        )

    # Group by prompt version
    versions_data = {}
    for classification in classifications:
        version = getattr(classification, "prompt_version", "v2")
        if version not in versions_data:
            versions_data[version] = {
                "classifications": [],
                "feedbacks": [],
            }
        versions_data[version]["classifications"].append(classification)

    # Get feedback for each classification
    feedback_query = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.created_at >= cutoff_date
    )
    if current_user:
        feedback_query = feedback_query.filter(ClassificationFeedback.user_id == current_user.id)

    feedbacks = feedback_query.all()
    feedback_map = {f.classification_id: f for f in feedbacks}

    # Calculate metrics for each version
    results = []
    version_stats = {}

    for version, data in versions_data.items():
        classifications = data["classifications"]
        total = len(classifications)

        # Calculate feedback metrics
        correct_count = 0
        feedback_count = 0

        for classification in classifications:
            feedback = feedback_map.get(classification.id)
            if feedback and feedback.is_correct is not None:
                feedback_count += 1
                if feedback.is_correct:
                    correct_count += 1

        accuracy = (correct_count / feedback_count * 100) if feedback_count > 0 else 0
        avg_confidence = sum(c.confidence for c in classifications) / total if total > 0 else 0
        avg_latency = sum(c.latency_ms for c in classifications) / total if total > 0 else 0

        result = PromptTestResult(
            prompt_version=version,
            total_classifications=total,
            feedback_count=feedback_count,
            correct_count=correct_count,
            accuracy_percentage=round(accuracy, 2),
            avg_confidence=round(avg_confidence, 2),
            avg_latency_ms=round(avg_latency, 1)
        )

        results.append(result)
        version_stats[version] = {
            "accuracy": accuracy,
            "correct": correct_count,
            "feedback_count": feedback_count,
            "result": result
        }

    # Find best version
    best_version = max(version_stats.items(), key=lambda x: x[1]["accuracy"])[0]
    best_stats = version_stats[best_version]

    # Compare versions for statistical significance
    significance_tests = {}
    versions_list = list(version_stats.keys())

    for i, v1 in enumerate(versions_list):
        for v2 in versions_list[i + 1:]:
            stats1 = version_stats[v1]
            stats2 = version_stats[v2]

            chi_sq, p_val = calculate_chi_squared(
                stats1["correct"],
                stats2["correct"],
                stats1["feedback_count"],
                stats2["feedback_count"]
            )

            significance_tests[f"{v1}_vs_{v2}"] = {
                "chi_squared": round(chi_sq, 2),
                "p_value": round(p_val, 4),
                "is_significant": p_val < 0.05
            }

    # Build comparison
    comparison = {
        "best_version": best_version,
        "best_accuracy": round(best_stats["accuracy"], 2),
        "improvements": {}
    }

    for version, stats in version_stats.items():
        if version != best_version:
            improvement = best_stats["accuracy"] - stats["accuracy"]
            comparison["improvements"][version] = round(improvement, 2)

    return ABTestResults(
        test_period_days=days,
        results=sorted(results, key=lambda x: x.accuracy_percentage, reverse=True),
        comparison=comparison,
        recommended_version=best_version,
        statistical_significance=significance_tests
    )


@router.get("/abtest/version-performance/{version}")
def get_version_performance(
    version: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get detailed performance metrics for a specific prompt version."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.prompt_version == version,
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if not classifications:
        return {
            "prompt_version": version,
            "total_classifications": 0,
            "metrics": {},
            "by_label": {}
        }

    # Get feedbacks
    feedback_query = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.created_at >= cutoff_date
    )
    if current_user:
        feedback_query = feedback_query.filter(ClassificationFeedback.user_id == current_user.id)

    feedbacks = feedback_query.all()
    feedback_map = {f.classification_id: f for f in feedbacks}

    # Overall metrics
    total = len(classifications)
    correct_with_feedback = sum(1 for c in classifications if feedback_map.get(c.id) and feedback_map.get(c.id).is_correct)
    feedback_count = sum(1 for c in classifications if feedback_map.get(c.id) and feedback_map.get(c.id).is_correct is not None)

    accuracy = (correct_with_feedback / feedback_count * 100) if feedback_count > 0 else 0
    avg_confidence = sum(c.confidence for c in classifications) / total
    avg_latency = sum(c.latency_ms for c in classifications) / total

    # By label
    by_label = {}
    for classification in classifications:
        label = classification.label
        if label not in by_label:
            by_label[label] = {"total": 0, "correct": 0, "avg_confidence": 0, "confidences": []}

        by_label[label]["total"] += 1
        by_label[label]["confidences"].append(classification.confidence)

        feedback = feedback_map.get(classification.id)
        if feedback and feedback.is_correct:
            by_label[label]["correct"] += 1

    # Calculate averages
    for label in by_label:
        confidences = by_label[label]["confidences"]
        by_label[label]["avg_confidence"] = round(sum(confidences) / len(confidences), 2) if confidences else 0
        by_label[label]["accuracy"] = round(by_label[label]["correct"] / by_label[label]["total"] * 100, 2)
        del by_label[label]["confidences"]

    return {
        "prompt_version": version,
        "test_period_days": days,
        "total_classifications": total,
        "feedback_count": feedback_count,
        "metrics": {
            "accuracy_percentage": round(accuracy, 2),
            "average_confidence": round(avg_confidence, 2),
            "average_latency_ms": round(avg_latency, 1),
        },
        "by_label": by_label
    }


@router.post("/abtest/select-best")
def select_best_prompt(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Automatically select and recommend the best prompt version."""
    results = get_abtest_results(days=days, db=db, current_user=current_user)

    if not results.results:
        return {
            "success": False,
            "message": "Not enough data to determine best version",
            "recommended_version": "v2"
        }

    best = results.results[0]  # Already sorted by accuracy

    return {
        "success": True,
        "recommended_version": best.prompt_version,
        "accuracy": best.accuracy_percentage,
        "reason": f"{best.prompt_version} has {best.accuracy_percentage}% accuracy based on {best.feedback_count} feedback responses",
        "comparison": results.comparison
    }
