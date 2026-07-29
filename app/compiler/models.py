"""
Database models for compiler submissions and saved snippets.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


class CompilerSubmission(Base):
    __tablename__ = "compiler_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String(30), nullable=False, index=True)
    code = Column(Text, nullable=False)
    stdin = Column(Text, default="", nullable=False)
    stdout = Column(Text, default="", nullable=False)
    stderr = Column(Text, default="", nullable=False)
    execution_time = Column(Float, default=0.0, nullable=False)
    memory = Column(Integer, nullable=True)
    exit_code = Column(Integer, nullable=True)
    status = Column(String(40), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="compiler_submissions")


class SavedCode(Base):
    __tablename__ = "saved_codes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    language = Column(String(30), nullable=False, index=True)
    code = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="saved_codes")

