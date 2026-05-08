from datetime import datetime
from database import SessionLocal, ActivityLog


def log_activity(
    action: str,
    user_id: int = None,
    details: str = None,
    ip_address: str = None,
    status: str = "success",
):
    """Log user activity to database."""
    db = SessionLocal()
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
            status=status,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Failed to log activity: {e}")
    finally:
        db.close()


def get_user_activity(user_id: int, limit: int = 100):
    """Get recent activity for a user."""
    db = SessionLocal()
    try:
        logs = (
            db.query(ActivityLog)
            .filter(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return logs
    finally:
        db.close()


def get_all_activity(limit: int = 500):
    """Get all activity logs (for admin)."""
    db = SessionLocal()
    try:
        logs = (
            db.query(ActivityLog)
            .order_by(ActivityLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return logs
    finally:
        db.close()
