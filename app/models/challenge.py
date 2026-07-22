"""
Challenge database model.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.connection import Base


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True, nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    category = Column(String(50), default="general")
    description = Column(Text, nullable=False)
    requirements = Column(Text, default="")
    functional_requirements = Column(Text, default="")
    non_functional_requirements = Column(Text, default="")
    expected_scale = Column(Text, default="")
    constraints = Column(Text, default="")
    estimated_time = Column(Integer, default=45)  # minutes
    tags = Column(JSON, default=list)
    icon = Column(String(50), default="server")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="challenge")
