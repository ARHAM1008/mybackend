"""
Interviews router: submit interviews and get history/details.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database.connection import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.challenge import Challenge
from app.models.interview import InterviewSession, InterviewAnswer
from app.models.score import Score
from app.models.feedback import AIFeedback
from app.schemas.interview import (
    InterviewSubmitRequest, InterviewDetailResponse, InterviewHistoryResponse,
    ScoreResponse, FeedbackResponse,
)
from app.services.ai_service import evaluate_interview

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("", response_model=InterviewDetailResponse, status_code=status.HTTP_201_CREATED)
async def submit_interview(
    data: InterviewSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit an interview and receive AI evaluation."""
    # Validate challenge
    challenge = db.query(Challenge).filter(Challenge.id == data.challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Create interview session
    session = InterviewSession(
        user_id=current_user.id,
        challenge_id=data.challenge_id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()

    # Store answers
    answer = InterviewAnswer(
        interview_id=session.id,
        database_choice=data.database_choice,
        cache_choice=data.cache_choice,
        auth_choice=data.auth_choice,
        architecture_choice=data.architecture_choice,
        communication_choice=data.communication_choice,
        storage_choice=data.storage_choice,
        queue_choice=data.queue_choice,
        monitoring_choice=data.monitoring_choice,
        architecture_explanation=data.architecture_explanation,
        api_design=data.api_design,
        scaling_strategy=data.scaling_strategy,
        database_design=data.database_design,
        failure_handling=data.failure_handling,
        security_design=data.security_design,
        cost_optimization=data.cost_optimization,
    )
    db.add(answer)

    # Run AI evaluation
    challenge_dict = {
        "title": challenge.title,
        "description": challenge.description,
        "requirements": challenge.requirements,
        "functional_requirements": challenge.functional_requirements,
        "non_functional_requirements": challenge.non_functional_requirements,
        "expected_scale": challenge.expected_scale,
    }
    answer_dict = data.model_dump(exclude={"challenge_id"})

    evaluation = await evaluate_interview(challenge_dict, answer_dict)

    # Store scores
    scores_data = evaluation.get("scores", {})
    score = Score(
        interview_id=session.id,
        architecture_score=scores_data.get("architecture_score", 0),
        database_score=scores_data.get("database_score", 0),
        scalability_score=scores_data.get("scalability_score", 0),
        availability_score=scores_data.get("availability_score", 0),
        consistency_score=scores_data.get("consistency_score", 0),
        security_score=scores_data.get("security_score", 0),
        api_design_score=scores_data.get("api_design_score", 0),
        cost_score=scores_data.get("cost_score", 0),
        monitoring_score=scores_data.get("monitoring_score", 0),
        overall_score=scores_data.get("overall_score", 0),
    )
    db.add(score)

    # Store feedback
    feedback_data = evaluation.get("feedback", {})
    feedback = AIFeedback(
        interview_id=session.id,
        strengths=feedback_data.get("strengths", []),
        weaknesses=feedback_data.get("weaknesses", []),
        recommendations=feedback_data.get("recommendations", []),
        follow_up_questions=feedback_data.get("follow_up_questions", []),
        overall_feedback=feedback_data.get("overall_feedback", ""),
        architecture_feedback=feedback_data.get("architecture_feedback", ""),
        database_feedback=feedback_data.get("database_feedback", ""),
        scalability_feedback=feedback_data.get("scalability_feedback", ""),
        security_feedback=feedback_data.get("security_feedback", ""),
    )
    db.add(feedback)

    # Update user skill level
    from sqlalchemy import func
    avg_score = (
        db.query(func.avg(Score.overall_score))
        .join(InterviewSession, Score.interview_id == InterviewSession.id)
        .filter(InterviewSession.user_id == current_user.id)
        .scalar()
    )
    if avg_score:
        from app.services.analytics_service import get_user_level
        current_user.skill_level = get_user_level(float(avg_score)).lower()

    db.commit()
    db.refresh(session)

    return _build_detail_response(session, challenge, answer, score, feedback)


@router.get("/history", response_model=InterviewHistoryResponse)
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's interview history."""
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.started_at.desc())
        .all()
    )

    interviews = []
    for session in sessions:
        challenge = db.query(Challenge).filter(Challenge.id == session.challenge_id).first()
        score = db.query(Score).filter(Score.interview_id == session.id).first()
        feedback = db.query(AIFeedback).filter(AIFeedback.interview_id == session.id).first()

        interviews.append(_build_detail_response(session, challenge, session.answer, score, feedback))

    return InterviewHistoryResponse(interviews=interviews, total=len(interviews))


@router.get("/{interview_id}", response_model=InterviewDetailResponse)
def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single interview session with full details."""
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == interview_id, InterviewSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Interview not found")

    challenge = db.query(Challenge).filter(Challenge.id == session.challenge_id).first()
    score = db.query(Score).filter(Score.interview_id == session.id).first()
    feedback = db.query(AIFeedback).filter(AIFeedback.interview_id == session.id).first()

    return _build_detail_response(session, challenge, session.answer, score, feedback)


def _build_detail_response(session, challenge, answer, score, feedback) -> InterviewDetailResponse:
    """Build a detailed interview response object."""
    answer_dict = None
    if answer:
        answer_dict = {
            "database_choice": answer.database_choice,
            "cache_choice": answer.cache_choice,
            "auth_choice": answer.auth_choice,
            "architecture_choice": answer.architecture_choice,
            "communication_choice": answer.communication_choice,
            "storage_choice": answer.storage_choice,
            "queue_choice": answer.queue_choice,
            "monitoring_choice": answer.monitoring_choice,
            "architecture_explanation": answer.architecture_explanation,
            "api_design": answer.api_design,
            "scaling_strategy": answer.scaling_strategy,
            "database_design": answer.database_design,
            "failure_handling": answer.failure_handling,
            "security_design": answer.security_design,
            "cost_optimization": answer.cost_optimization,
        }

    return InterviewDetailResponse(
        id=session.id,
        challenge_id=session.challenge_id,
        challenge_title=challenge.title if challenge else "",
        challenge_difficulty=challenge.difficulty if challenge else "",
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        answer=answer_dict,
        score=ScoreResponse.model_validate(score) if score else None,
        feedback=FeedbackResponse.model_validate(feedback) if feedback else None,
    )
