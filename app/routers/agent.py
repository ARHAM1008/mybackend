"""
AI Agent Router: Repository-aware coding assistant with file analysis capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.groq_service import agent_analyze, chat_completion
from loguru import logger

router = APIRouter(prefix="/agent", tags=["AI Agent"])


class AgentRequest(BaseModel):
    query: str
    files: Optional[list[dict]] = None
    model: Optional[str] = None


class AgentFileRequest(BaseModel):
    path: str
    content: str


@router.post("/analyze")
async def analyze(
    data: AgentRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze code files with the AI agent (streaming response)."""
    logger.info(f"Agent analyze request from user {current_user.id}: query_len={len(data.query)}, files={len(data.files or [])}")

    return StreamingResponse(
        agent_analyze(
            query=data.query,
            files=data.files,
            model=data.model,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/explain")
async def explain_code(
    data: AgentFileRequest,
    current_user: User = Depends(get_current_user),
):
    """Explain a piece of code."""
    prompt = f"""Explain the following code in detail. Include:
1. What the code does
2. The programming language and key concepts used
3. Time and space complexity analysis
4. Potential improvements or edge cases

```\n{data.content}\n```"""

    response = await chat_completion(
        message=prompt,
        model=data.model if hasattr(data, 'model') else None,
        system_prompt="You are an expert code reviewer. Provide clear, detailed explanations.",
        temperature=0.3,
    )

    return {"response": response}


@router.post("/refactor")
async def refactor_code(
    data: AgentFileRequest,
    current_user: User = Depends(get_current_user),
):
    """Refactor code for better readability and maintainability."""
    prompt = f"""Refactor the following code to improve:
1. Readability and maintainability
2. Performance
3. Error handling
4. Follow best practices

Original code:
```\n{data.content}\n```

Provide the refactored code with explanations of the changes made."""

    response = await chat_completion(
        message=prompt,
        system_prompt="You are an expert code refactoring specialist. Provide clean, production-ready code.",
        temperature=0.3,
    )

    return {"response": response}


@router.post("/debug")
async def debug_code(
    data: AgentFileRequest,
    current_user: User = Depends(get_current_user),
):
    """Debug code and find issues."""
    prompt = f"""Debug the following code. Identify:
1. Syntax errors
2. Logic errors
3. Runtime issues
4. Security vulnerabilities
5. Performance bottlenecks

Code:
```\n{data.content}\n```

Provide the fixed code with explanations of each issue found."""

    response = await chat_completion(
        message=prompt,
        system_prompt="You are an expert debugger. Find and fix all issues in the code.",
        temperature=0.3,
    )

    return {"response": response}


@router.post("/generate-tests")
async def generate_tests(
    data: AgentFileRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate unit tests for code."""
    prompt = f"""Generate comprehensive unit tests for the following code.
Include:
1. Test cases for normal inputs
2. Edge cases
3. Error cases
4. Mock external dependencies if needed

Code:
```\n{data.content}\n```

Provide the test code with explanations."""

    response = await chat_completion(
        message=prompt,
        system_prompt="You are an expert in test-driven development. Generate thorough, well-structured tests.",
        temperature=0.3,
    )

    return {"response": response}


@router.post("/review")
async def review_code(
    data: AgentFileRequest,
    current_user: User = Depends(get_current_user),
):
    """Perform a comprehensive code review."""
    prompt = f"""Perform a thorough code review of the following code. Cover:
1. Code quality and style
2. Architecture and design patterns
3. Performance considerations
4. Security concerns
5. Error handling
6. Test coverage suggestions
7. Documentation needs

Code:
```\n{data.content}\n```

Provide a structured review with actionable recommendations."""

    response = await chat_completion(
        message=prompt,
        system_prompt="You are a senior staff engineer conducting a code review. Be thorough and constructive.",
        temperature=0.3,
    )

    return {"response": response}