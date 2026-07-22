"""
Authentication router: register, login, profile, password management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
    ChangePasswordRequest, UserResponse, UserUpdateRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse)
def update_profile(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile."""
    if data.name is not None:
        current_user.name = data.name
    if data.bio is not None:
        current_user.bio = data.bio
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset (mock implementation)."""
    user = db.query(User).filter(User.email == data.email).first()
    # Always return success to avoid email enumeration
    return {"message": "If an account exists with this email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a token (mock implementation)."""
    # In production, validate the reset token
    # For now, accept any token and reset for demo purposes
    return {"message": "Password has been reset successfully. Please login with your new password."}
