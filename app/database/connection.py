"""
Database connection setup using SQLAlchemy.
Supports both SQLite (development) and PostgreSQL (production).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


def _build_database_url(url: str) -> str:
    """Ensure postgres URLs use the installed psycopg v3 driver."""
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# Configure engine based on database type
if settings.is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite only
        echo=False,
    )
else:
    engine = create_engine(
        _build_database_url(settings.DATABASE_URL),
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Declarative base for models
class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables. Used for development/initial setup."""
    Base.metadata.create_all(bind=engine)
