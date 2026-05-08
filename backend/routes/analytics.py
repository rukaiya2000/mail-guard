"""Analytics and reporting routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from collections import defaultdict

from database import get_db, User, ClassificationLog
from schemas import MetricsResponse, HistoryItem, ActivityLogResponse
from auth import get_optional_user, get_current_user
from export_utils import export_to_csv, export_to_pdf
from activity_logger import log_activity, get_user_activity, get_all_activity
from auth_utils import require_admin
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get aggregated metrics from classification history."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)
    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)
    logs = query.all()

    if not logs:
        return MetricsResponse(
            total_calls=0,
            average_latency_ms=0.0,
            error_rate=0.0,
            total_tokens_used=0,
            estimated_cost=0.0
        )

    total_calls = len(logs)
    average_latency_ms = sum(log.latency_ms for log in logs) / total_calls
    total_tokens_used = sum(log.tokens_used for log in logs)

    total_attempted = db.query(func.count(ClassificationLog.id)).scalar()
    error_count = db.query(func.count(ClassificationLog.id)).filter(
        ClassificationLog.success == False
    ).scalar()
    error_rate = (error_count / total_attempted * 100) if total_attempted > 0 else 0.0

    estimated_cost = (total_tokens_used / 1000) * 0.002

    return MetricsResponse(
        total_calls=total_calls,
        average_latency_ms=round(average_latency_ms, 2),
        error_rate=round(error_rate, 2),
        total_tokens_used=total_tokens_used,
        estimated_cost=round(estimated_cost, 4)
    )


@router.get("/history", response_model=list[HistoryItem])
def get_history(
    label: str = None,
    search: str = None,
    start_date: str = None,
    end_date: str = None,
    confidence_min: float = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get classification results with optional filtering."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if label and label.upper() != 'ALL':
        query = query.filter(ClassificationLog.label == label.upper())

    if search:
        query = query.filter(ClassificationLog.email_snippet.ilike(f"%{search}%"))

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(ClassificationLog.timestamp >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(ClassificationLog.timestamp <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

    if confidence_min is not None:
        confidence_min = max(0, min(1, confidence_min))
        query = query.filter(ClassificationLog.confidence >= confidence_min)

    logs = (
        query
        .order_by(ClassificationLog.timestamp.desc())
        .limit(50)
        .all()
    )

    return [
        HistoryItem(
            timestamp=log.timestamp,
            label=log.label,
            confidence=log.confidence,
            email_snippet=log.email_snippet
        )
        for log in logs
    ]


@router.get("/analytics")
def get_analytics(
    start_date: str = None,
    end_date: str = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get advanced analytics including distribution and trends. Paginated for performance."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)
    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(ClassificationLog.timestamp >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(ClassificationLog.timestamp <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Limit for performance
    if limit > 10000:
        limit = 10000

    logs = query.order_by(ClassificationLog.timestamp.desc()).limit(limit).all()

    if not logs:
        return {
            "distribution": {"PHISHING": 0, "SPAM": 0, "LEGITIMATE": 0},
            "trends": [],
            "top_hours": []
        }

    distribution = defaultdict(int)
    for log in logs:
        distribution[log.label] += 1

    hourly_data = defaultdict(lambda: {"count": 0, "avg_confidence": []})
    for log in logs:
        hour = log.timestamp.strftime("%Y-%m-%d %H:00")
        hourly_data[hour]["count"] += 1
        hourly_data[hour]["avg_confidence"].append(log.confidence)

    trends = []
    for hour in sorted(hourly_data.keys())[-24:]:
        data = hourly_data[hour]
        trends.append({
            "time": hour,
            "count": data["count"],
            "avg_confidence": sum(data["avg_confidence"]) / len(data["avg_confidence"])
        })

    top_hours = sorted(
        hourly_data.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )[:5]
    top_hours = [{"time": k, "count": v["count"]} for k, v in top_hours]

    return {
        "distribution": dict(distribution),
        "trends": trends,
        "top_hours": top_hours
    }


@router.get("/export/csv")
def export_csv(
    label: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Export classifications as CSV."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if label and label.upper() != 'ALL':
        query = query.filter(ClassificationLog.label == label.upper())

    logs = query.order_by(ClassificationLog.timestamp.desc()).limit(500).all()

    if not logs:
        raise HTTPException(status_code=404, detail="No classifications to export")

    csv_data = export_to_csv(logs)

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=classifications.csv"}
    )


@router.get("/export/pdf")
def export_pdf(
    label: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Export classifications as PDF report."""
    query = db.query(ClassificationLog).filter(ClassificationLog.success == True)

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    if label and label.upper() != 'ALL':
        query = query.filter(ClassificationLog.label == label.upper())

    logs = query.order_by(ClassificationLog.timestamp.desc()).limit(500).all()

    if not logs:
        raise HTTPException(status_code=404, detail="No classifications to export")

    user_name = current_user.username if current_user else "User"
    pdf_data = export_to_pdf(logs, user_name=user_name)

    return StreamingResponse(
        iter([pdf_data]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"}
    )


@router.get("/activity", response_model=list[ActivityLogResponse])
def get_activity(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """Get user's activity logs."""
    logs = get_user_activity(current_user.id, limit=limit)
    return logs


@router.get("/admin/activity", response_model=list[ActivityLogResponse])
def get_admin_activity(
    limit: int = 500,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all activity logs (admin only)."""
    require_admin(current_user)

    logs = get_all_activity(limit=limit)
    logger.info(f"Admin {current_user.username} accessed all activity logs")

    return logs
