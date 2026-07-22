"""
AI Feedback database model.
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.connection import Base


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)

    # AI evaluation results
    strengths = Column(JSON, default=list)  # List of strength strings
    weaknesses = Column(JSON, default=list)  # List of weakness strings
    recommendations = Column(JSON, default=list)  # List of recommendation strings
    follow_up_questions = Column(JSON, default=list)  # List of follow-up question strings

    # Detailed feedback text
    overall_feedback = Column(Text, default="")
    architecture_feedback = Column(Text, default="")
    database_feedback = Column(Text, default="")
    scalability_feedback = Column(Text, default="")
    security_feedback = Column(Text, default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("InterviewSession", back_populates="feedback")
