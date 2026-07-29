"""
Pydantic schemas for the online compiler API.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CompilerLanguage = Literal["python", "c", "cpp", "java", "javascript"]
AiCompilerAction = Literal[
    "explain",
    "review",
    "bugs",
    "optimize",
    "comments",
    "complexity",
]


class CompilerRunRequest(BaseModel):
    language: CompilerLanguage
    code: str = Field(min_length=1, max_length=100_000)
    stdin: str = Field(default="", max_length=20_000)


class CompilerRunResponse(BaseModel):
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0
    memory: int | None = None
    exit_code: int | None = None
    status: str


class CompilerSubmissionRead(CompilerRunResponse):
    id: int
    language: str
    code: str
    stdin: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    submissions: list[CompilerSubmissionRead]
    total: int
    page: int
    page_size: int


class SavedCodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    language: CompilerLanguage
    code: str = Field(min_length=1, max_length=100_000)


class SavedCodeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    language: CompilerLanguage | None = None
    code: str | None = Field(default=None, min_length=1, max_length=100_000)


class SavedCodeRead(BaseModel):
    id: int
    title: str
    language: str
    code: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SavedCodeListResponse(BaseModel):
    snippets: list[SavedCodeRead]


class AiCompilerRequest(BaseModel):
    action: AiCompilerAction
    language: CompilerLanguage
    code: str = Field(min_length=1, max_length=100_000)


class AiCompilerResponse(BaseModel):
    result: str

