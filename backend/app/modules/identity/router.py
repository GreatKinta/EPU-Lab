from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, select

from app.core.errors import AppError
from app.core.security import Admin, CurrentUser, Db, issue_token, password_hash
from app.modules.audit.service import record
from app.modules.identity.models import User
from app.modules.identity.schemas import LoginInput, UserCreate, UserOut, UserPatch

router = APIRouter(tags=["identity"])
_attempts = defaultdict(deque)
_lock = Lock()
_dummy_hash = password_hash.hash("timing-only-password-not-a-user")


@router.post("/auth/login")
def login(body: LoginInput, request: Request, db: Db):
    key = request.client.host if request.client else "unknown"
    now = monotonic()
    with _lock:
        # Bound limiter memory and expire inactive entries.
        for stale in [k for k, v in _attempts.items() if not v or v[-1] < now - 60]:
            del _attempts[stale]
        attempts = _attempts[key]
        while attempts and attempts[0] < now - 60:
            attempts.popleft()
        if len(attempts) >= 10:
            raise AppError(429, "RATE_LIMIT", "Thử lại sau một phút")
        attempts.append(now)
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    valid = password_hash.verify(body.password, user.password_hash if user else _dummy_hash)
    if not user or not valid or not user.is_active:
        raise AppError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng")
    return {
        "access_token": issue_token(user),
        "token_type": "bearer",
        "user": UserOut.model_validate(user),
    }


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.get("/users")
def users(
    db: Db, admin: Admin, page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100)
):
    return {
        "items": [
            UserOut.model_validate(x)
            for x in db.scalars(
                select(User)
                .order_by(User.created_at, User.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(User)),
        "page": page,
        "page_size": page_size,
    }


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Db, admin: Admin):
    values = body.model_dump(exclude={"password"})
    user = User(**values, password_hash=password_hash.hash(body.password))
    db.add(user)
    db.flush()
    record(db, admin, "user", user.id, "UserCreated", after={"role": user.role})
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: UUID, body: UserPatch, db: Db, admin: Admin):
    user = db.get(User, user_id, with_for_update=True)
    if not user:
        raise AppError(404, "NOT_FOUND", "Không tìm thấy tài khoản")
    values = body.model_dump(exclude_unset=True)
    if any(v is None for v in values.values()):
        raise AppError(422, "VALIDATION_ERROR", "Không được đặt trường tài khoản thành null")
    if user.id == admin.id and (
        values.get("is_active") is False or values.get("role", "admin") != "admin"
    ):
        raise AppError(
            409, "SELF_LOCKOUT", "Không thể tự hạ quyền hoặc khóa tài khoản quản trị đang dùng"
        )
    if "password" in values:
        user.password_hash = password_hash.hash(values.pop("password"))
    before = {"role": user.role, "is_active": user.is_active}
    for key, value in values.items():
        setattr(user, key, value)
    record(
        db,
        admin,
        "user",
        user.id,
        "UserUpdated",
        before=before,
        after={"role": user.role, "is_active": user.is_active},
    )
    db.flush()
    return user
