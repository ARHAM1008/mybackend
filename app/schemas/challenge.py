"""
Challenge schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class ChallengeCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=200)
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    category: str = "general"
    description: str = Field(..., min_length=10)
    requirements: str = ""
    functional_requirements: str = ""
    non_functional_requirements: str = ""
    expected_scale: str = ""
    constraints: str = ""
    estimated_time: int = 45
    tags: list[str] = []
    icon: str = "server"


class ChallengeUpdate(BaseModel):
    title: str | None = None
    difficulty: str | None = None
    category: str | None = None
    description: str | None = None
    requirements: str | None = None
    functional_requirements: str | None = None
    non_functional_requirements: str | None = None
    expected_scale: str | None = None
    constraints: str | None = None
    estimated_time: int | None = None
    tags: list[str] | None = None
    icon: str | None = None
    is_active: int | None = None


class ChallengeResponse(BaseModel):
    id: int
    title: str
    slug: str
    difficulty: str
    category: str
    description: str
    requirements: str
    functional_requirements: str
    non_functional_requirements: str
    expected_scale: str
    constraints: str
    estimated_time: int
    tags: list
    icon: str
    is_active: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChallengeListResponse(BaseModel):
    challenges: list[ChallengeResponse]
    total: int