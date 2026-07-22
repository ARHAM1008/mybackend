"""
Analytics router: dashboard stats, progress tracking, leaderboard.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.analytics_service import get_dashboard_stats, get_progress_data, get_leaderboard
from app.schemas.analytics import DashboardResponse, ProgressResponse, LeaderboardResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics for the current user."""
    data = get_dashboard_stats(db, current_user.id)
    return DashboardResponse(**data)


@router.get("/progress", response_model=ProgressResponse)
def progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed progress analytics."""
    data = get_progress_data(db, current_user.id)
    return ProgressResponse(**data)


@router.get("/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get global leaderboard."""
    data = get_leaderboard(db, current_user.id)
    return LeaderboardResponse(**data)
