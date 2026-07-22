"""
Analytics schemas for dashboard and progress data.
"""

from pydantic import BaseModel
from typing import List, Optional


class DashboardStats(BaseModel):
    total_interviews: int = 0
    average_score: float = 0.0
    current_level: str = "Beginner"
    completed_challenges: int = 0
    total_challenges: int = 0


class SkillScore(BaseModel):
    category: str
    score: float


class RecentInterview(BaseModel):
    id: int
    challenge_title: str
    difficulty: str
    overall_score: float
    completed_at: Optional[str] = None


class WeeklyActivity(BaseModel):
    day: str
    count: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    skill_scores: List[SkillScore] = []
    recent_interviews: List[RecentInterview] = []
    weekly_activity: List[WeeklyActivity] = []
    score_history: List[dict] = []


class ProgressResponse(BaseModel):
    score_trend: List[dict] = []
    category_progress: List[dict] = []
    improvement_rate: float = 0.0
    strongest_area: str = ""
    weakest_area: str = ""


class LeaderboardEntry(BaseModel):
    rank: int
    user_name: str
    average_score: float
    total_interviews: int
    level: str


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry] = []
    user_rank: Optional[int] = None
