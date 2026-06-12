"""FastAPI dependency providers — DB session, auth, config."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.core.config import PipelineConfig, Settings
from refund_pilot.core.security import decode_access_token
from refund_pilot.db.session import AsyncSessionLocal

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
_settings = Settings()
_pipeline_config = PipelineConfig()


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield async DB session, close on exit."""
    async with AsyncSessionLocal() as session:
        yield session


def get_pipeline_config() -> PipelineConfig:
    """Return singleton PipelineConfig."""
    return _pipeline_config


def get_settings() -> Settings:
    """Return singleton Settings."""
    return _settings


async def require_admin(
    token: str = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> object:
    """Verify JWT and return AdminUser. Raises 401 if invalid."""
    from sqlalchemy import select

    from refund_pilot.db.models import AdminUser

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token, _settings.jwt_secret_key, _settings.jwt_algorithm)
        user_id = cast(str | None, payload.get("sub"))
        if not user_id:
            raise credentials_error
    except Exception:
        raise credentials_error from None

    from uuid import UUID

    result = await db.execute(select(AdminUser).where(AdminUser.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_error
    return user


async def require_superadmin(admin: object = Depends(require_admin)) -> object:
    """Raise 403 if admin user is not superadmin."""
    if getattr(admin, "role", None) != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
    return admin
