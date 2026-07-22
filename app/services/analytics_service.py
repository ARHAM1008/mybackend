"""
Analytics service for computing dashboard stats, progress, and leaderboard.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta, timezone
from app.models.user import User
from app.models.interview import InterviewSession
from app.models.score import Score
from app.models.challenge import Challenge


def get_user_level(avg_score: float) -> str:
    """Determine user level based on average score."""
    if avg_score >= 85:
        return "Expert"
    elif avg_score >= 70:
        return "Advanced"
    elif avg_score >= 50:
        return "Intermediate"
    else:
        return "Beginner"


def get_dashboard_stats(db: Session, user_id: int) -> dict:
    """Get dashboard statistics for a user."""
    # Total interviews
    total_interviews = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id, InterviewSession.status == "completed")
        .count()
    )

    # Average score
    avg_result = (
        db.query(func.avg(Score.overall_score))
        .join(InterviewSession, Score.interview_id == InterviewSession.id)
        .filter(InterviewSession.user_id == user_id)
        .scalar()
    )
    average_score = round(float(avg_result), 1) if avg_result else 0.0

    # Total challenges
    total_challenges = db.query(Challenge).filter(Challenge.is_active == 1).count()

    # Unique completed challenges
    completed_challenges = (
        db.query(func.count(func.distinct(InterviewSession.challenge_id)))
        .filter(InterviewSession.user_id == user_id, InterviewSession.status == "completed")
        .scalar()
    ) or 0

    return {
        "stats": {
            "total_interviews": total_interviews,
            "average_score": average_score,
            "current_level": get_user_level(average_score),
            "completed_challenges": completed_challenges,
            "total_challenges": total_challenges,
        },
        "skill_scores": _get_skill_scores(db, user_id),
        "recent_interviews": _get_recent_interviews(db, user_id),
        "weekly_activity": _get_weekly_activity(db, user_id),
        "score_history": _get_score_history(db, user_id),
    }


def _get_skill_scores(db: Session, user_id: int) -> list:
    """Get average scores per category for radar chart."""
    scores = (
        db.query(
            func.avg(Score.architecture_score),
            func.avg(Score.database_score),
            func.avg(Score.scalability_score),
            func.avg(Score.availability_score),
            func.avg(Score.consistency_score),
            func.avg(Score.security_score),
            func.avg(Score.api_design_score),
            func.avg(Score.cost_score),
            func.avg(Score.monitoring_score),
        )
        .join(InterviewSession, Score.interview_id == InterviewSession.id)
        .filter(InterviewSession.user_id == user_id)
        .first()
    )

    if not scores or all(s is None for s in scores):
        return []

    categories = [
        "Architecture", "Database", "Scalability", "Availability",
        "Consistency", "Security", "API Design", "Cost", "Monitoring"
    ]

    return [
        {"category": cat, "score": round(float(s), 1) if s else 0}
        for cat, s in zip(categories, scores)
    ]


def _get_recent_interviews(db: Session, user_id: int, limit: int = 5) -> list:
    """Get recent interview sessions with scores."""
    sessions = (
        db.query(InterviewSession, Challenge.title, Challenge.difficulty, Score.overall_score)
        .join(Challenge, InterviewSession.challenge_id == Challenge.id)
        .outerjoin(Score, Score.interview_id == InterviewSession.id)
        .filter(InterviewSession.user_id == user_id, InterviewSession.status == "completed")
        .order_by(desc(InterviewSession.completed_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": session.id,
            "challenge_title": title,
            "difficulty": difficulty,
            "overall_score": round(float(score), 1) if score else 0,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }
        for session, title, difficulty, score in sessions
    ]


def _get_weekly_activity(db: Session, user_id: int) -> list:
    """Get interview count per day for the last 7 days."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    now = datetime.now(timezone.utc)
    result = []

    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        count = (
            db.query(InterviewSession)
            .filter(
                InterviewSession.user_id == user_id,
                func.date(InterviewSession.started_at) == day.date(),
            )
            .count()
        )
        result.append({"day": days[day.weekday()], "count": count})

    return result


def _get_score_history(db: Session, user_id: int, limit: int = 20) -> list:
    """Get score history over time for line chart."""
    sessions = (
        db.query(Score.overall_score, InterviewSession.completed_at)
        .join(InterviewSession, Score.interview_id == InterviewSession.id)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.completed_at)
        .limit(limit)
        .all()
    )

    return [
        {
            "score": round(float(score), 1),
            "date": completed.isoformat() if completed else "",
            "index": i + 1,
        }
        for i, (score, completed) in enumerate(sessions)
    ]


def get_progress_data(db: Session, user_id: int) -> dict:
    """Get detailed progress analytics."""
    skill_scores = _get_skill_scores(db, user_id)
    score_history = _get_score_history(db, user_id, limit=50)

    # Calculate improvement rate
    improvement_rate = 0.0
    if len(score_history) >= 2:
        first_half = score_history[: len(score_history) // 2]
        second_half = score_history[len(score_history) // 2:]
        first_avg = sum(s["score"] for s in first_half) / len(first_half)
        second_avg = sum(s["score"] for s in second_half) / len(second_half)
        improvement_rate = round(second_avg - first_avg, 1)

    strongest = max(skill_scores, key=lambda x: x["score"])["category"] if skill_scores else ""
    weakest = min(skill_scores, key=lambda x: x["score"])["category"] if skill_scores else ""

    return {
        "score_trend": score_history,
        "category_progress": skill_scores,
        "improvement_rate": improvement_rate,
        "strongest_area": strongest,
        "weakest_area": weakest,
    }


def get_leaderboard(db: Session, current_user_id: int) -> dict:
    """Get global leaderboard based on average scores."""
    results = (
        db.query(
            User.id,
            User.name,
            func.avg(Score.overall_score).label("avg_score"),
            func.count(InterviewSession.id).label("total"),
        )
        .join(InterviewSession, InterviewSession.user_id == User.id)
        .join(Score, Score.interview_id == InterviewSession.id)
        .filter(InterviewSession.status == "completed")
        .group_by(User.id, User.name)
        .order_by(desc("avg_score"))
        .limit(50)
        .all()
    )

    entries = []
    user_rank = None
    for rank, (uid, name, avg_score, total) in enumerate(results, 1):
        avg_float = round(float(avg_score), 1)
        entries.append({
            "rank": rank,
            "user_name": name,
            "average_score": avg_float,
            "total_interviews": total,
            "level": get_user_level(avg_float),
        })
        if uid == current_user_id:
            user_rank = rank

    return {"entries": entries, "user_rank": user_rank}
