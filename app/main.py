"""
CodeMentor Backend – FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.database.connection import create_tables, SessionLocal
from app.database.seed import seed_challenges, seed_admin

# Import routers
from app.routers import auth, challenges, interviews, ai, analytics, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} API ({settings.ENVIRONMENT})")

    # Create database tables
    create_tables()
    logger.info("Database tables created")

    # Seed data
    db = SessionLocal()
    try:
        seed_challenges(db)
        seed_admin(db)
    finally:
        db.close()

    logger.info("Seed data loaded")
    yield
    logger.info("Shutting down")


# Create FastAPI app
app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="AI System Design Interview Platform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(challenges.router, prefix="/api")
app.include_router(interviews.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """Health check for Render."""
    return {"status": "healthy"}
