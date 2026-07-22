"""
Interview session and answer database models.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.connection import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False, index=True)
    status = Column(String(20), default="in_progress")  # in_progress, completed, draft
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    challenge = relationship("Challenge", back_populates="interview_sessions")
    answer = relationship("InterviewAnswer", back_populates="session", uselist=False, cascade="all, delete-orphan")
    score = relationship("Score", back_populates="session", uselist=False, cascade="all, delete-orphan")
    feedback = relationship("AIFeedback", back_populates="session", uselist=False, cascade="all, delete-orphan")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Architecture choices
    database_choice = Column(String(50), default="")
    cache_choice = Column(String(50), default="")
    auth_choice = Column(String(50), default="")
    architecture_choice = Column(String(50), default="")
    communication_choice = Column(String(50), default="")
    storage_choice = Column(String(50), default="")
    queue_choice = Column(String(50), default="")
    monitoring_choice = Column(String(50), default="")

    # Free-text explanations
    architecture_explanation = Column(Text, default="")
    api_design = Column(Text, default="")
    scaling_strategy = Column(Text, default="")
    database_design = Column(Text, default="")
    failure_handling = Column(Text, default="")
    security_design = Column(Text, default="")
    cost_optimization = Column(Text, default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("InterviewSession", back_populates="answer")
