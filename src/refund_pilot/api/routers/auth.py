"""Auth endpoints: register (first-run), login, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.api.dependencies import get_db, get_settings, require_superadmin
from refund_pilot.core.config import Settings
from refund_pilot.core.security import create_access_token, hash_password, verify_password
from refund_pilot.db.models import AdminUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "readonly"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Create admin user. Open only when zero admin_users exist (first-run bootstrap)."""
    count = await db.scalar(select(func.count()).select_from(AdminUser))
    if count and count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration closed. Use superadmin to create users.",
        )
    user = AdminUser(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role="superadmin",  # first user is always superadmin
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(
        str(user.id),
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        settings.jwt_expire_hours,
    )
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate admin user, return JWT."""
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(
        str(user.id),
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        settings.jwt_expire_hours,
    )
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    current_user: AdminUser = Depends(require_superadmin),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Extend JWT for authenticated admin."""
    token = create_access_token(
        str(current_user.id),
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        settings.jwt_expire_hours,
    )
    return TokenResponse(access_token=token)


class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "readonly"


@router.post("/admin/users", response_model=dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_superadmin),
) -> dict[str, str]:
    """Superadmin creates new user. Superadmin can assign any role; admin can only assign readonly."""
    actor_role = getattr(admin, "role", "readonly")
    if actor_role == "admin" and body.role != "readonly":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only create readonly users"
        )
    user = AdminUser(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_active=True,
        created_by=admin.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": str(user.id), "username": user.username, "role": user.role}
