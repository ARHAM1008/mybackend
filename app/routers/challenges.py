"""
Challenges router: CRUD operations for system design challenges.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database.connection import get_db
from app.core.dependencies import get_current_user, get_admin_user
from app.models.user import User
from app.models.challenge import Challenge
from app.schemas.challenge import (
    ChallengeCreate, ChallengeUpdate, ChallengeResponse, ChallengeListResponse,
)

router = APIRouter(prefix="/challenges", tags=["Challenges"])


@router.get("", response_model=ChallengeListResponse)
def list_challenges(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all active challenges with optional filters."""
    query = db.query(Challenge).filter(Challenge.is_active == 1)

    if difficulty:
        query = query.filter(Challenge.difficulty == difficulty)
    if category:
        query = query.filter(Challenge.category == category)
    if search:
        query = query.filter(
            Challenge.title.ilike(f"%{search}%") | Challenge.description.ilike(f"%{search}%")
        )

    total = query.count()
    challenges = query.order_by(Challenge.id).offset(skip).limit(limit).all()

    return ChallengeListResponse(
        challenges=[ChallengeResponse.model_validate(c) for c in challenges],
        total=total,
    )


@router.get("/{challenge_id}", response_model=ChallengeResponse)
def get_challenge(challenge_id: int, db: Session = Depends(get_db)):
    """Get a single challenge by ID."""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found",
        )
    return ChallengeResponse.model_validate(challenge)


@router.post("", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
def create_challenge(
    data: ChallengeCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Create a new challenge (admin only)."""
    existing = db.query(Challenge).filter(Challenge.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Challenge with this slug already exists")

    challenge = Challenge(**data.model_dump())
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return ChallengeResponse.model_validate(challenge)


@router.put("/{challenge_id}", response_model=ChallengeResponse)
def update_challenge(
    challenge_id: int,
    data: ChallengeUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Update a challenge (admin only)."""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(challenge, key, value)

    db.commit()
    db.refresh(challenge)
    return ChallengeResponse.model_validate(challenge)


@router.delete("/{challenge_id}")
def delete_challenge(
    challenge_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a challenge (admin only)."""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    db.delete(challenge)
    db.commit()
    return {"message": "Challenge deleted successfully"}
