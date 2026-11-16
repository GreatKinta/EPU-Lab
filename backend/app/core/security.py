from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.modules.identity.models import User

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
Db = Annotated[Session, Depends(get_db, scope="function")]


def issue_token(user: User):
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": "labchain",
            "aud": "labchain-web",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def get_user(db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    try:
        if not credentials:
            raise ValueError()
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            audience="labchain-web",
            issuer="labchain",
            options={"require": ["sub", "exp", "iat"]},
        )
        user = db.get(User, UUID(payload["sub"]))
        if not user or not user.is_active:
            raise ValueError()
        return user
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise AppError(401, "UNAUTHENTICATED", "Vui lòng đăng nhập lại") from None


CurrentUser = Annotated[User, Depends(get_user)]


def require_staff(user: CurrentUser):
    if user.role not in ("staff", "admin"):
        raise AppError(403, "FORBIDDEN", "Chỉ cán bộ được thực hiện thao tác này")
    return user


def require_admin(user: CurrentUser):
    if user.role != "admin":
        raise AppError(403, "FORBIDDEN", "Chỉ quản trị viên được thực hiện thao tác này")
    return user


Staff = Annotated[User, Depends(require_staff)]
Admin = Annotated[User, Depends(require_admin)]
