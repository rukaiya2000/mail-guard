"""Real-time monitoring and system health metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

from database import get_db, User, ClassificationLog, ClassificationFeedback
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


class SystemMetrics(BaseModel):
    """Real-time system health metrics."""
    timestamp: str
    total_classifications_24h: int
    classifications_per_hour: float
    average_latency_ms: float
    error_rate_percent: float
    success_rate_percent: float
    average_confidence: float
    model_distribution: dict
    label_distribution: dict
    most_used_model: str
    most_common_label: str


class HealthStatus(BaseModel):
    """System health status."""
    status: str  # "healthy", "degraded", "critical"
    checks: dict  # {"latency": "ok", "error_rate": "high", ...}
    alerts: list[str]


class RealtimeMetrics(BaseModel):
    """Simplified metrics for real-time dashboard."""
    timestamp: str
    classifications_last_hour: int
    success_rate: float
    avg_latency: float
    avg_confidence: float
    top_model: str
    system_status: str


def check_latency_health(avg_latency: float) -> tuple[str, Optional[str]]:
    """Check if latency is healthy."""
    if avg_latency < 2000:
        return "ok", None
    elif avg_latency < 4000:
        return "warning", f"Latency elevated: {avg_latency:.0f}ms"
    else:
        return "critical", f"Latency critical: {avg_latency:.0f}ms"


def check_error_rate_health(error_rate: float) -> tuple[str, Optional[str]]:
    """Check if error rate is healthy."""
    if error_rate < 2:
        return "ok", None
    elif error_rate < 5:
        return "warning", f"Error rate elevated: {error_rate:.1f}%"
    else:
        return "critical", f"Error rate critical: {error_rate:.1f}%"


def check_confidence_health(avg_confidence: float) -> tuple[str, Optional[str]]:
    """Check if model confidence is healthy."""
    if avg_confidence > 0.80:
        return "ok", None
    elif avg_confidence > 0.70:
        return "warning", f"Confidence low: {avg_confidence:.3f}"
    else:
        return "critical", f"Confidence critical: {avg_confidence:.3f}"


@router.get("/monitoring/metrics")
def get_system_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get real-time system metrics."""
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)
    cutoff_1h = now - timedelta(hours=1)

    # Query last 24 hours
    query_24h = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_24h
    )

    if current_user:
        query_24h = query_24h.filter(ClassificationLog.user_id == current_user.id)

    classifications_24h = query_24h.all()
    successful_24h = [c for c in classifications_24h if c.success]
    failed_24h = [c for c in classifications_24h if not c.success]

    # Query last hour
    query_1h = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_1h
    )

    if current_user:
        query_1h = query_1h.filter(ClassificationLog.user_id == current_user.id)

    classifications_1h = query_1h.all()

    # Calculate metrics
    total_24h = len(classifications_24h)
    success_rate = (len(successful_24h) / total_24h * 100) if total_24h > 0 else 0
    error_rate = (len(failed_24h) / total_24h * 100) if total_24h > 0 else 0

    avg_latency = (
        sum(c.latency_ms for c in successful_24h) / len(successful_24h)
        if successful_24h else 0
    )

    avg_confidence = (
        sum(c.confidence for c in successful_24h) / len(successful_24h)
        if successful_24h else 0
    )

    # Classifications per hour
    classifications_per_hour = total_24h / 24 if total_24h > 0 else 0

    # Model distribution
    model_dist = {}
    for c in successful_24h:
        model = c.model or "unknown"
        model_dist[model] = model_dist.get(model, 0) + 1

    # Label distribution
    label_dist = {}
    for c in successful_24h:
        label_dist[c.label] = label_dist.get(c.label, 0) + 1

    most_used_model = max(model_dist, key=model_dist.get) if model_dist else "unknown"
    most_common_label = max(label_dist, key=label_dist.get) if label_dist else "unknown"

    return SystemMetrics(
        timestamp=now.isoformat(),
        total_classifications_24h=total_24h,
        classifications_per_hour=round(classifications_per_hour, 2),
        average_latency_ms=round(avg_latency, 1),
        error_rate_percent=round(error_rate, 2),
        success_rate_percent=round(success_rate, 2),
        average_confidence=round(avg_confidence, 3),
        model_distribution=model_dist,
        label_distribution=label_dist,
        most_used_model=most_used_model,
        most_common_label=most_common_label
    )


@router.get("/monitoring/health")
def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get system health status with alerts."""
    metrics = get_system_metrics(db=db, current_user=current_user)

    checks = {}
    alerts = []

    # Check latency
    latency_status, latency_alert = check_latency_health(metrics.average_latency_ms)
    checks["latency"] = latency_status
    if latency_alert:
        alerts.append(latency_alert)

    # Check error rate
    error_status, error_alert = check_error_rate_health(metrics.error_rate_percent)
    checks["error_rate"] = error_status
    if error_alert:
        alerts.append(error_alert)

    # Check confidence
    confidence_status, confidence_alert = check_confidence_health(metrics.average_confidence)
    checks["model_confidence"] = confidence_status
    if confidence_alert:
        alerts.append(confidence_alert)

    # Overall status
    if any(v == "critical" for v in checks.values()):
        overall_status = "critical"
    elif any(v == "warning" for v in checks.values()):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthStatus(
        status=overall_status,
        checks=checks,
        alerts=alerts
    )


@router.get("/monitoring/realtime")
def get_realtime_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get simplified real-time metrics for dashboard."""
    metrics = get_system_metrics(db=db, current_user=current_user)
    health = get_system_health(db=db, current_user=current_user)

    return RealtimeMetrics(
        timestamp=metrics.timestamp,
        classifications_last_hour=int(metrics.classifications_per_hour),
        success_rate=metrics.success_rate_percent,
        avg_latency=metrics.average_latency_ms,
        avg_confidence=metrics.average_confidence,
        top_model=metrics.most_used_model,
        system_status=health.status
    )


@router.get("/monitoring/dashboard")
def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get complete dashboard data in single request."""
    now = datetime.utcnow()

    # Real-time metrics
    realtime = get_realtime_metrics(db=db, current_user=current_user)
    health = get_system_health(db=db, current_user=current_user)
    metrics = get_system_metrics(db=db, current_user=current_user)

    # Hourly trends (last 24 hours)
    cutoff_24h = now - timedelta(hours=24)
    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_24h
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    # Group by hour
    hourly_data = {}
    for c in classifications:
        hour_key = c.timestamp.strftime("%Y-%m-%d %H:00")

        if hour_key not in hourly_data:
            hourly_data[hour_key] = {
                "count": 0,
                "success": 0,
                "avg_latency": 0.0,
                "avg_confidence": 0.0,
                "latencies": [],
                "confidences": []
            }

        hourly_data[hour_key]["count"] += 1
        if c.success:
            hourly_data[hour_key]["success"] += 1
        hourly_data[hour_key]["latencies"].append(c.latency_ms)
        hourly_data[hour_key]["confidences"].append(c.confidence)

    # Calculate hourly averages
    hourly_trends = []
    for hour_key in sorted(hourly_data.keys()):
        data = hourly_data[hour_key]
        avg_latency = sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else 0
        avg_confidence = sum(data["confidences"]) / len(data["confidences"]) if data["confidences"] else 0

        hourly_trends.append({
            "time": hour_key,
            "classifications": data["count"],
            "success_rate": (data["success"] / data["count"] * 100) if data["count"] > 0 else 0,
            "avg_latency_ms": round(avg_latency, 1),
            "avg_confidence": round(avg_confidence, 3)
        })

    return {
        "timestamp": now.isoformat(),
        "realtime": realtime,
        "health": health,
        "summary": {
            "total_24h": metrics.total_classifications_24h,
            "success_rate": metrics.success_rate_percent,
            "error_rate": metrics.error_rate_percent,
            "avg_latency": metrics.average_latency_ms,
            "avg_confidence": metrics.average_confidence
        },
        "distribution": {
            "by_model": metrics.model_distribution,
            "by_label": metrics.label_distribution
        },
        "hourly_trends": hourly_trends[-24:],  # Last 24 hours
        "ready_for_production": health.status == "healthy"
    }


@router.get("/monitoring/sla-compliance")
def check_sla_compliance(
    target_uptime_percent: float = 99.5,
    target_latency_p99: int = 5000,
    target_error_rate: float = 1.0,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Check compliance with SLA targets."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if not classifications:
        return {"error": "No data available"}

    # Uptime (success rate)
    successful = len([c for c in classifications if c.success])
    uptime = (successful / len(classifications) * 100) if classifications else 0
    uptime_compliant = uptime >= target_uptime_percent

    # Latency P99
    successful_classifications = [c for c in classifications if c.success]
    latencies = sorted([c.latency_ms for c in successful_classifications])
    p99_index = int(len(latencies) * 0.99)
    p99_latency = latencies[p99_index] if p99_index < len(latencies) else 0
    latency_compliant = p99_latency <= target_latency_p99

    # Error rate
    error_rate = ((len(classifications) - successful) / len(classifications) * 100) if classifications else 0
    error_compliant = error_rate <= target_error_rate

    overall_compliant = uptime_compliant and latency_compliant and error_compliant

    return {
        "period_days": days,
        "overall_compliant": overall_compliant,
        "metrics": {
            "uptime": {
                "target": target_uptime_percent,
                "actual": round(uptime, 2),
                "compliant": uptime_compliant
            },
            "latency_p99_ms": {
                "target": target_latency_p99,
                "actual": round(p99_latency, 1),
                "compliant": latency_compliant
            },
            "error_rate": {
                "target": target_error_rate,
                "actual": round(error_rate, 2),
                "compliant": error_compliant
            }
        }
    }
