from fastapi import HTTPException, status
from auth import CurrentUser


def require_admin(user: CurrentUser) -> CurrentUser:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def require_analyst(user: CurrentUser) -> CurrentUser:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analyst or admin access required")
