from fastapi import HTTPException, status
from database import User


def require_admin(user: User) -> User:
    """Check if user has admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def require_analyst(user: User) -> User:
    """Check if user has analyst or admin role."""
    if user.role not in ["analyst", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or admin access required"
        )
    return user


def require_role(required_role: str):
    """Factory for role-based access control."""
    def check_role(user: User) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user
    return check_role
