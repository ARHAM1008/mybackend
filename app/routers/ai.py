"""
AI router: follow-up questions and additional evaluation.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.interview import InterviewSession
from app.models.challenge import Challenge
from app.services.ai_service import generate_followup_response

router = APIRouter(prefix="/ai", tags=["AI"])


class FollowUpRequest(BaseModel):
    interview_id: int
    question: str


class FollowUpResponse(BaseModel):
    response: str
    hints: list = []
    key_concepts: list = []


@router.post("/follow-up", response_model=FollowUpResponse)
async def follow_up(
    data: FollowUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask an AI follow-up question about an interview."""
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.id == data.interview_id,
            InterviewSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Interview not found")

    challenge = db.query(Challenge).filter(Challenge.id == session.challenge_id).first()
    challenge_dict = {
        "title": challenge.title if challenge else "",
        "description": challenge.description if challenge else "",
    }

    answer_dict = {}
    if session.answer:
        answer_dict = {
            "database_choice": session.answer.database_choice,
            "cache_choice": session.answer.cache_choice,
            "architecture_choice": session.answer.architecture_choice,
        }

    result = await generate_followup_response(challenge_dict, answer_dict, data.question)
    return FollowUpResponse(**result)
