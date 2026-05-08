"""Model drift detection: monitor performance degradation over time."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

from database import get_db, User, ClassificationLog, ClassificationFeedback
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["drift"])


class DriftAlert(BaseModel):
    """Alert for detected model drift."""
    alert_type: str  # "accuracy_drop", "confidence_drop", "latency_increase"
    severity: str  # "critical", "warning", "info"
    description: str
    metric_name: str
    previous_value: float
    current_value: float
    change_percent: float
    recommendation: str


class DriftAnalysis(BaseModel):
    """Complete drift analysis for a time period."""
    period_days: int
    total_classifications: int
    alerts: list[DriftAlert]
    has_drift: bool
    overall_health: str  # "healthy", "degraded", "critical"
    trend_analysis: dict


def calculate_moving_average(values: list, window: int = 7) -> list:
    """Calculate moving average for trend detection."""
    if len(values) < window:
        return values

    moving_avg = []
    for i in range(len(values) - window + 1):
        avg = sum(values[i:i+window]) / window
        moving_avg.append(avg)
    return moving_avg


def detect_accuracy_drift(
    daily_accuracies: list,
    threshold_drop: float = 5.0  # Alert if accuracy drops > 5%
) -> Optional[DriftAlert]:
    """Detect if accuracy is dropping significantly."""
    if len(daily_accuracies) < 14:
        return None  # Need 2 weeks of data

    # Compare first week vs last week
    first_week = sum(daily_accuracies[:7]) / 7 if len(daily_accuracies) >= 7 else 0
    last_week = sum(daily_accuracies[-7:]) / 7

    drop = first_week - last_week
    drop_percent = (drop / first_week * 100) if first_week > 0 else 0

    if drop_percent > threshold_drop:
        return DriftAlert(
            alert_type="accuracy_drop",
            severity="critical" if drop_percent > 10 else "warning",
            description=f"Model accuracy dropped {drop_percent:.1f}% (from {first_week:.1f}% to {last_week:.1f}%)",
            metric_name="accuracy",
            previous_value=first_week,
            current_value=last_week,
            change_percent=drop_percent,
            recommendation="Consider retraining model with new feedback or reviewing recent phishing patterns"
        )

    return None


def detect_confidence_drift(
    daily_confidences: list,
    threshold_drop: float = 0.08  # Alert if confidence drops > 0.08
) -> Optional[DriftAlert]:
    """Detect if model confidence is decreasing."""
    if len(daily_confidences) < 14:
        return None

    first_week_avg = sum(daily_confidences[:7]) / 7 if len(daily_confidences) >= 7 else 0
    last_week_avg = sum(daily_confidences[-7:]) / 7

    drop = first_week_avg - last_week_avg

    if drop > threshold_drop:
        drop_percent = (drop / first_week_avg * 100) if first_week_avg > 0 else 0
        return DriftAlert(
            alert_type="confidence_drop",
            severity="warning",
            description=f"Model confidence decreased by {drop:.3f} ({drop_percent:.1f}%)",
            metric_name="avg_confidence",
            previous_value=first_week_avg,
            current_value=last_week_avg,
            change_percent=drop_percent,
            recommendation="Model may be encountering new email patterns. Consider running adversarial tests."
        )

    return None


def detect_latency_increase(
    daily_latencies: list,
    threshold_increase: float = 20.0  # Alert if latency increases > 20%
) -> Optional[DriftAlert]:
    """Detect if processing latency is increasing."""
    if len(daily_latencies) < 7:
        return None

    first_week_avg = sum(daily_latencies[:7]) / 7 if len(daily_latencies) >= 7 else 0
    last_week_avg = sum(daily_latencies[-7:]) / 7 if len(daily_latencies[-7:]) > 0 else 0

    if first_week_avg == 0:
        return None

    increase_percent = ((last_week_avg - first_week_avg) / first_week_avg) * 100

    if increase_percent > threshold_increase:
        return DriftAlert(
            alert_type="latency_increase",
            severity="info" if increase_percent < 50 else "warning",
            description=f"Processing latency increased {increase_percent:.1f}% ({first_week_avg:.0f}ms → {last_week_avg:.0f}ms)",
            metric_name="latency_ms",
            previous_value=first_week_avg,
            current_value=last_week_avg,
            change_percent=increase_percent,
            recommendation="Check LLM API performance or consider model optimization"
        )

    return None


def detect_label_distribution_shift(
    daily_distributions: list,
    threshold: float = 0.15  # Alert if distribution changes > 15%
) -> Optional[DriftAlert]:
    """Detect if email classification distribution is shifting (concept drift)."""
    if len(daily_distributions) < 7:
        return None

    # Average distribution from first week vs last week
    first_week_dist = {}
    last_week_dist = {}

    for label in ["PHISHING", "SPAM", "LEGITIMATE"]:
        first_week_counts = sum(
            d.get(label, 0) for d in daily_distributions[:7]
        )
        last_week_counts = sum(
            d.get(label, 0) for d in daily_distributions[-7:]
        )

        first_week_dist[label] = first_week_counts
        last_week_dist[label] = last_week_counts

    # Check if any label distribution changed significantly
    total_first = sum(first_week_dist.values())
    total_last = sum(last_week_dist.values())

    if total_first == 0 or total_last == 0:
        return None

    for label in ["PHISHING", "SPAM", "LEGITIMATE"]:
        first_pct = (first_week_dist[label] / total_first) if total_first > 0 else 0
        last_pct = (last_week_dist[label] / total_last) if total_last > 0 else 0

        change = abs(first_pct - last_pct)

        if change > threshold:
            return DriftAlert(
                alert_type="distribution_shift",
                severity="info",
                description=f"Email distribution shifted: {label} {first_pct*100:.1f}% → {last_pct*100:.1f}%",
                metric_name=f"distribution_{label}",
                previous_value=first_pct,
                current_value=last_pct,
                change_percent=change * 100,
                recommendation="Email threat landscape may be changing. Review recent patterns and consider model retraining."
            )

    return None


@router.get("/drift/status")
def get_drift_status(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get current drift detection status."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_date,
        ClassificationLog.success == True
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if len(classifications) < 7:
        return {
            "status": "insufficient_data",
            "message": f"Need at least 7 days of data. Current: {len(classifications)} classifications"
        }

    # Group by day
    daily_stats = {}
    for classification in classifications:
        day = classification.timestamp.date()

        if day not in daily_stats:
            daily_stats[day] = {
                "classifications": 0,
                "correct": 0,
                "total_confidence": 0.0,
                "total_latency": 0.0,
                "distribution": {"PHISHING": 0, "SPAM": 0, "LEGITIMATE": 0}
            }

        daily_stats[day]["classifications"] += 1
        daily_stats[day]["total_confidence"] += classification.confidence
        daily_stats[day]["total_latency"] += classification.latency_ms
        daily_stats[day]["distribution"][classification.label] += 1

    # Get feedback for accuracy
    feedback_query = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.created_at >= cutoff_date
    )
    if current_user:
        feedback_query = feedback_query.filter(ClassificationFeedback.user_id == current_user.id)

    feedbacks = feedback_query.all()
    feedback_map = {f.classification_id: f for f in feedbacks}

    # Count correct classifications per day
    for classification in classifications:
        day = classification.timestamp.date()
        feedback = feedback_map.get(classification.id)
        if feedback and feedback.is_correct:
            daily_stats[day]["correct"] += 1

    # Calculate daily metrics
    sorted_days = sorted(daily_stats.keys())
    daily_accuracies = []
    daily_confidences = []
    daily_latencies = []
    daily_distributions = []

    for day in sorted_days:
        stats = daily_stats[day]

        # Accuracy (from feedback)
        feedback_on_day = [
            f for f in feedbacks
            if f.created_at.date() == day
        ]
        if feedback_on_day:
            accuracy = sum(1 for f in feedback_on_day if f.is_correct) / len(feedback_on_day) * 100
        else:
            accuracy = 0

        daily_accuracies.append(accuracy)

        # Confidence
        avg_conf = (stats["total_confidence"] / stats["classifications"]
                   if stats["classifications"] > 0 else 0)
        daily_confidences.append(avg_conf)

        # Latency
        avg_latency = (stats["total_latency"] / stats["classifications"]
                      if stats["classifications"] > 0 else 0)
        daily_latencies.append(avg_latency)

        daily_distributions.append(stats["distribution"])

    # Detect drifts
    alerts = []

    accuracy_drift = detect_accuracy_drift(daily_accuracies)
    if accuracy_drift:
        alerts.append(accuracy_drift)

    confidence_drift = detect_confidence_drift(daily_confidences)
    if confidence_drift:
        alerts.append(confidence_drift)

    latency_drift = detect_latency_increase(daily_latencies)
    if latency_drift:
        alerts.append(latency_drift)

    distribution_drift = detect_label_distribution_shift(daily_distributions)
    if distribution_drift:
        alerts.append(distribution_drift)

    # Overall health
    if any(a.severity == "critical" for a in alerts):
        overall_health = "critical"
    elif any(a.severity == "warning" for a in alerts):
        overall_health = "degraded"
    else:
        overall_health = "healthy"

    # Trends
    moving_avg_accuracy = calculate_moving_average(daily_accuracies, 7)
    moving_avg_confidence = calculate_moving_average(daily_confidences, 7)

    return DriftAnalysis(
        period_days=days,
        total_classifications=len(classifications),
        alerts=alerts,
        has_drift=len(alerts) > 0,
        overall_health=overall_health,
        trend_analysis={
            "accuracy_trend": "improving" if (moving_avg_accuracy[-1] > moving_avg_accuracy[0] if moving_avg_accuracy else False) else "declining",
            "confidence_trend": "stable",
            "current_accuracy": daily_accuracies[-1] if daily_accuracies else 0,
            "current_confidence": daily_confidences[-1] if daily_confidences else 0,
            "current_latency_ms": daily_latencies[-1] if daily_latencies else 0
        }
    )


@router.get("/drift/recommendations")
def get_drift_recommendations(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get actionable recommendations based on detected drift."""
    drift_status = get_drift_status(days=days, db=db, current_user=current_user)

    recommendations = []

    for alert in drift_status.alerts:
        recommendations.append({
            "priority": alert.severity,
            "issue": alert.description,
            "action": alert.recommendation
        })

    if not recommendations:
        recommendations.append({
            "priority": "info",
            "issue": "No significant drift detected",
            "action": "Continue monitoring. Current model is stable."
        })

    return {
        "overall_status": drift_status.overall_health,
        "recommendations": recommendations,
        "retraining_suggested": drift_status.overall_health in ["critical", "degraded"]
    }
