from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
import uuid

from backend.db.models.user import User
from backend.db.models.refresh_token import RefreshToken
from backend.api.schemas.auth import UserCreate, UserResponse, TokenResponse, UserUpdate, ChangePasswordRequest
from backend.api.deps import get_db, get_current_user, oauth2_scheme
from backend.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    add_token_to_blocklist,
    decode_token,
    logger
)
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists."
        )
        
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password[:72]),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # Authenticate User
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password[:72], user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Create access token
    access_token = create_access_token(subject=user.id)
    
    # Create raw UUID refresh token and hash it
    import hashlib
    from datetime import datetime, timedelta, timezone
    from backend.config.settings import get_settings
    settings = get_settings()
    
    raw_refresh_token = str(uuid.uuid4())
    token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    # Store refresh token hash in DB
    refresh_token_obj = RefreshToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(refresh_token_obj)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "bearer"
    }

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    import hashlib
    from datetime import datetime, timezone, timedelta
    from backend.config.settings import get_settings
    
    token_hash = hashlib.sha256(req.refresh_token.encode()).hexdigest()
    
    # Verify refresh token in DB
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_obj = result.scalar_one_or_none()
    
    if not token_obj or token_obj.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token"
        )
        
    if token_obj.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
        
    # Rotate refresh token (delete old, create new)
    await db.delete(token_obj)
    
    user_id = token_obj.user_id
    access_token = create_access_token(subject=user_id)
    
    new_raw_refresh_token = str(uuid.uuid4())
    new_token_hash = hashlib.sha256(new_raw_refresh_token.encode()).hexdigest()
    
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    new_token_obj = RefreshToken(
        token_hash=new_token_hash,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(new_token_obj)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_raw_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(
    req: RefreshRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    import hashlib
    # 1. Delete the refresh token from the database
    token_hash = hashlib.sha256(req.refresh_token.encode()).hexdigest()
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_obj = result.scalar_one_or_none()
    if token_obj:
        await db.delete(token_obj)
        await db.commit()
            
    # 2. Blocklist the current access token in Redis
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            await add_token_to_blocklist(jti, exp)
    except Exception as e:
        logger.error("Failed to blocklist access token during logout", error=str(e))
        
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> Any:
    return current_user

@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update current user's profile information."""
    if user_in.first_name is not None:
        current_user.first_name = user_in.first_name
    if user_in.last_name is not None:
        current_user.last_name = user_in.last_name
        
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Change the current user's password."""
    if not verify_password(password_data.old_password[:72], current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
        
    current_user.password_hash = get_password_hash(password_data.new_password[:72])
    db.add(current_user)
    await db.commit()
    
    return {"message": "Password updated successfully"}
