"""
Admin router: user management, challenge management, platform analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.connection import get_db
from app.core.dependencies import get_admin_user
from app.models.user import User
from app.models.challenge import Challenge
from app.models.interview import InterviewSession
from app.models.score import Score
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users")
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    user_list = []
    for user in users:
        interview_count = (
            db.query(InterviewSession)
            .filter(InterviewSession.user_id == user.id, InterviewSession.status == "completed")
            .count()
        )
        avg_score = (
            db.query(func.avg(Score.overall_score))
            .join(InterviewSession, Score.interview_id == InterviewSession.id)
            .filter(InterviewSession.user_id == user.id)
            .scalar()
        )

        user_list.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "skill_level": user.skill_level,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "total_interviews": interview_count,
            "average_score": round(float(avg_score), 1) if avg_score else 0,
        })

    return {"users": user_list, "total": total}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.get("/analytics")
def admin_analytics(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get platform-wide analytics (admin only)."""
    total_users = db.query(User).count()
    total_interviews = db.query(InterviewSession).filter(InterviewSession.status == "completed").count()
    total_challenges = db.query(Challenge).count()

    avg_score = db.query(func.avg(Score.overall_score)).scalar()

    # Top challenges by usage
    top_challenges = (
        db.query(
            Challenge.title,
            func.count(InterviewSession.id).label("count"),
        )
        .join(InterviewSession, InterviewSession.challenge_id == Challenge.id)
        .group_by(Challenge.title)
        .order_by(func.count(InterviewSession.id).desc())
        .limit(5)
        .all()
    )

    return {
        "total_users": total_users,
        "total_interviews": total_interviews,
        "total_challenges": total_challenges,
        "average_score": round(float(avg_score), 1) if avg_score else 0,
        "top_challenges": [{"title": t, "count": c} for t, c in top_challenges],
    }
