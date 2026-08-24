from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Role, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserCreate, UserResponse
from app.services.audit import record_audit
from app.core.logger import logger
from app.core.config import settings
from app.core.rate_limit import LoginFailureLimiter

router = APIRouter(prefix="/auth")
login_limiter = LoginFailureLimiter(settings.login_failure_limit, settings.login_failure_window_seconds)


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{payload.username.strip().lower()}"
    if login_limiter.blocked(limiter_key):
        logger.warning("login temporarily blocked username=%s ip=%s", payload.username, client_ip)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="登录失败次数过多，请稍后再试")
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.hashed_password) or not user.is_active:
        login_limiter.record_failure(limiter_key)
        logger.warning("login failed username=%s ip=%s", payload.username, client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    login_limiter.reset(limiter_key)
    logger.info("login success user_id=%s ip=%s", user.id, client_ip)
    record_audit(db, user_id=user.id, action="login", resource="auth", description="用户登录成功")
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="用户注册")
def register(payload: RegisterRequest, db: DbSession) -> UserResponse:
    existing = db.scalar(select(User).where((User.username == payload.username) | (User.email == payload.email)))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名或邮箱已存在")
    role = db.scalar(select(Role).where(Role.name == "user"))
    if role is None:
        role = Role(name="user", description="普通用户")
        db.add(role)
        db.flush()
    user = User(username=payload.username, email=payload.email, hashed_password=hash_password(payload.password), display_name=payload.display_name, roles=[role])
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, username=user.username, email=user.email, display_name=user.display_name, is_active=user.is_active, roles=[item.name for item in user.roles])


@router.get("/me", response_model=UserResponse, summary="获取当前用户")
def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=[role.name for role in user.roles],
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="创建用户")
def create_user(payload: UserCreate, _: AdminUser, db: DbSession) -> UserResponse:
    if db.scalar(select(User).where(User.username == payload.username)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    roles = list(db.scalars(select(Role).where(Role.name.in_(payload.roles))))
    if len(roles) != len(set(payload.roles)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="包含不存在的角色")
    user = User(
        username=payload.username,
        email=f"{payload.username}@local.invalid",
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
        roles=roles,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=[role.name for role in user.roles],
    )
