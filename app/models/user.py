"""
User database model.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # "user" or "admin"
    bio = Column(Text, default="")
    avatar_url = Column(String(500), default="")
    skill_level = Column(String(20), default="beginner")  # beginner, intermediate, advanced
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
