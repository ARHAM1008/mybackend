"""
Score database model for AI evaluation results.
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.connection import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Individual category scores (0-100)
    architecture_score = Column(Float, default=0.0)
    database_score = Column(Float, default=0.0)
    scalability_score = Column(Float, default=0.0)
    availability_score = Column(Float, default=0.0)
    consistency_score = Column(Float, default=0.0)
    security_score = Column(Float, default=0.0)
    api_design_score = Column(Float, default=0.0)
    cost_score = Column(Float, default=0.0)
    monitoring_score = Column(Float, default=0.0)

    # Overall score
    overall_score = Column(Float, default=0.0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("InterviewSession", back_populates="score")
