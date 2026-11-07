"""认证接口：注册、登录、查看当前用户。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.deps import get_current_user, get_db
from app.models import User
from app.schemas.auth import CurrentUserOut, LoginIn, RegisterIn, TokenOut
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="注册",
)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> UserOut:
    return auth_service.register(db, payload.username, payload.phone, payload.password)


@router.post("/login", response_model=TokenOut, summary="登录,返回令牌")
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = auth_service.authenticate(db, payload.username, payload.password)
    return TokenOut(
        access_token=create_access_token(user.id),
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=CurrentUserOut, summary="当前登录用户")
def me(current_user: User = Depends(get_current_user)) -> CurrentUserOut:
    return CurrentUserOut(
        id=current_user.id,
        username=current_user.username,
        balance=current_user.balance,
        roles=[role.name for role in current_user.roles],
    )
