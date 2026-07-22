"""
Interview schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class InterviewSubmitRequest(BaseModel):
    challenge_id: int

    # Architecture choices
    database_choice: str = Field(default="", description="e.g., PostgreSQL, MongoDB")
    cache_choice: str = Field(default="", description="e.g., Redis, Memcached, None")
    auth_choice: str = Field(default="", description="e.g., JWT, OAuth, Session")
    architecture_choice: str = Field(default="", description="e.g., Monolith, Microservices, Serverless")
    communication_choice: str = Field(default="", description="e.g., REST, gRPC, WebSocket")
    storage_choice: str = Field(default="", description="e.g., AWS S3, Local Storage")
    queue_choice: str = Field(default="", description="e.g., Kafka, RabbitMQ, None")
    monitoring_choice: str = Field(default="", description="e.g., Prometheus, Grafana, ELK")

    # Free-text explanations
    architecture_explanation: str = ""
    api_design: str = ""
    scaling_strategy: str = ""
    database_design: str = ""
    failure_handling: str = ""
    security_design: str = ""
    cost_optimization: str = ""


class ScoreResponse(BaseModel):
    architecture_score: float
    database_score: float
    scalability_score: float
    availability_score: float
    consistency_score: float
    security_score: float
    api_design_score: float
    cost_score: float
    monitoring_score: float
    overall_score: float

    model_config = {"from_attributes": True}


class FeedbackResponse(BaseModel):
    strengths: list
    weaknesses: list
    recommendations: list
    follow_up_questions: list
    overall_feedback: str
    architecture_feedback: str
    database_feedback: str
    scalability_feedback: str
    security_feedback: str

    model_config = {"from_attributes": True}


class InterviewDetailResponse(BaseModel):
    id: int
    challenge_id: int
    challenge_title: str = ""
    challenge_difficulty: str = ""
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    answer: Optional[dict] = None
    score: Optional[ScoreResponse] = None
    feedback: Optional[FeedbackResponse] = None

    model_config = {"from_attributes": True}


class InterviewHistoryResponse(BaseModel):
    interviews: List[InterviewDetailResponse]
    total: int
