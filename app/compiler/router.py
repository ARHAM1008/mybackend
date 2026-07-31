"""
Compiler API routes.
"""

from datetime import datetime, timezone
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.compiler.models import CompilerSubmission, SavedCode
from app.compiler.schemas import (
    AiCompilerRequest,
    AiCompilerResponse,
    CompilerRunRequest,
    CompilerRunResponse,
    CompilerSubmissionRead,
    SavedCodeCreate,
    SavedCodeListResponse,
    SavedCodeRead,
    SavedCodeUpdate,
    SubmissionListResponse,
)
from app.compiler.service import CompilerService
from app.core.dependencies import get_current_user
from app.database.connection import get_db
from app.models.user import User


router = APIRouter(prefix="/compiler", tags=["Compiler"])
compiler_service = CompilerService()
_rate_buckets: dict[int, list[float]] = {}


def _enforce_rate_limit(user_id: int, max_requests: int = 30, window_seconds: int = 60) -> None:
    now = time.time()
    bucket = [stamp for stamp in _rate_buckets.get(user_id, []) if now - stamp < window_seconds]
    if len(bucket) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many compiler requests. Please slow down.")
    bucket.append(now)
    _rate_buckets[user_id] = bucket


@router.post("/run", response_model=CompilerRunResponse)
async def run_code(
    payload: CompilerRunRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _enforce_rate_limit(current_user.id)
    result = await compiler_service.run(payload.language, payload.code, payload.stdin)

    submission = CompilerSubmission(
        user_id=current_user.id,
        language=payload.language,
        code=payload.code,
        stdin=payload.stdin,
        stdout=result.stdout,
        stderr=result.stderr,
        execution_time=result.execution_time,
        memory=result.memory,
        exit_code=result.exit_code,
        status=result.status,
    )
    db.add(submission)
    db.commit()

    return CompilerRunResponse(**result.__dict__)


@router.get("/history", response_model=SubmissionListResponse)
def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    search: str = "",
    language: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(CompilerSubmission).filter(CompilerSubmission.user_id == current_user.id)
    if language:
        query = query.filter(CompilerSubmission.language == language)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(CompilerSubmission.code.ilike(like), CompilerSubmission.stdout.ilike(like), CompilerSubmission.stderr.ilike(like)))

    total = query.count()
    submissions = (
        query.order_by(CompilerSubmission.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return SubmissionListResponse(submissions=submissions, total=total, page=page, page_size=page_size)


@router.delete("/history/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission = db.query(CompilerSubmission).filter(
        CompilerSubmission.id == submission_id,
        CompilerSubmission.user_id == current_user.id,
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    db.delete(submission)
    db.commit()


@router.get("/saved", response_model=SavedCodeListResponse)
def list_saved_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snippets = db.query(SavedCode).filter(SavedCode.user_id == current_user.id).order_by(SavedCode.updated_at.desc()).all()
    return SavedCodeListResponse(snippets=snippets)


@router.post("/saved", response_model=SavedCodeRead, status_code=status.HTTP_201_CREATED)
def create_saved_code(
    payload: SavedCodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snippet = SavedCode(user_id=current_user.id, title=payload.title, language=payload.language, code=payload.code)
    db.add(snippet)
    db.commit()
    db.refresh(snippet)
    return snippet


@router.patch("/saved/{snippet_id}", response_model=SavedCodeRead)
def update_saved_code(
    snippet_id: int,
    payload: SavedCodeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snippet = db.query(SavedCode).filter(SavedCode.id == snippet_id, SavedCode.user_id == current_user.id).first()
    if not snippet:
        raise HTTPException(status_code=404, detail="Saved code not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(snippet, key, value)
    snippet.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(snippet)
    return snippet


@router.post("/saved/{snippet_id}/duplicate", response_model=SavedCodeRead, status_code=status.HTTP_201_CREATED)
def duplicate_saved_code(
    snippet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snippet = db.query(SavedCode).filter(SavedCode.id == snippet_id, SavedCode.user_id == current_user.id).first()
    if not snippet:
        raise HTTPException(status_code=404, detail="Saved code not found")

    copy = SavedCode(
        user_id=current_user.id,
        title=f"{snippet.title} Copy",
        language=snippet.language,
        code=snippet.code,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


@router.delete("/saved/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_code(
    snippet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snippet = db.query(SavedCode).filter(SavedCode.id == snippet_id, SavedCode.user_id == current_user.id).first()
    if not snippet:
        raise HTTPException(status_code=404, detail="Saved code not found")
    db.delete(snippet)
    db.commit()


@router.post("/ai", response_model=AiCompilerResponse)
async def compiler_ai(
    payload: AiCompilerRequest,
    current_user: User = Depends(get_current_user),
):
    prompts = {
        "explain": "Explain this code clearly and concisely.",
        "review": "Review this code for maintainability, readability, and correctness.",
        "bugs": "Find likely bugs and edge cases in this code.",
        "optimize": "Suggest practical optimizations for this code.",
        "comments": "Generate helpful comments for this code without over-commenting.",
        "complexity": "Analyze the time and space complexity of this code.",
    }
    fallback = (
        f"### {payload.action.title()}\n\n"
        f"AI is ready to analyze this {payload.language} code. "
        "Configure GROQ_API_KEY to receive live model feedback."
    )

    from app.services.groq_service import GroqServiceError, chat_completion, is_groq_configured

    if not is_groq_configured():
        return AiCompilerResponse(result=fallback)

    try:
        result = await chat_completion(
            message=(
                f"{prompts[payload.action]}\n\nLanguage: {payload.language}\n\n"
                f"```{payload.language}\n{payload.code}\n```"
            ),
            system_prompt="You are CodeMentor's coding coach. Respond in concise markdown.",
            temperature=0.4,
            max_tokens=1200,
        )
        return AiCompilerResponse(result=result or fallback)
    except GroqServiceError as exc:
        return AiCompilerResponse(result=f"{fallback}\n\n_{exc.user_message}_")
    except Exception:
        return AiCompilerResponse(result=fallback)


