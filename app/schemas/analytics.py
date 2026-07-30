"""
Analytics schemas for dashboard and progress data.
"""

from pydantic import BaseModel


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
    completed_at: str | None = None


class WeeklyActivity(BaseModel):
    day: str
    count: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    skill_scores: list[SkillScore] = []
    recent_interviews: list[RecentInterview] = []
    weekly_activity: list[WeeklyActivity] = []
    score_history: list[dict] = []


class ProgressResponse(BaseModel):
    score_trend: list[dict] = []
    category_progress: list[dict] = []
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
    entries: list[LeaderboardEntry] = []
    user_rank: int | None = None