"""
Challenge schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
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
    tags: List[str] = []
    icon: str = "server"


class ChallengeUpdate(BaseModel):
    title: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    functional_requirements: Optional[str] = None
    non_functional_requirements: Optional[str] = None
    expected_scale: Optional[str] = None
    constraints: Optional[str] = None
    estimated_time: Optional[int] = None
    tags: Optional[List[str]] = None
    icon: Optional[str] = None
    is_active: Optional[int] = None


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
    challenges: List[ChallengeResponse]
    total: int
