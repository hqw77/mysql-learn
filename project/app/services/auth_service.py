"""认证业务：注册与登录。

密码进数据库之前先哈希；登录时用哈希校验，明文不落库、不进日志。
"""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models import User


def register(db: Session, username: str, phone: str, password: str) -> User:
    """注册新用户。用户名或手机号重复时抛 ConflictError(409)。"""
    exists = db.scalar(
        select(User).where(or_(User.username == username, User.phone == phone))
    )
    if exists is not None:
        raise ConflictError("用户名或手机号已被注册")

    user = User(username=username, phone=phone, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:          # 并发下仍可能撞唯一键
        db.rollback()
        raise ConflictError("用户名或手机号已被注册") from exc
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    """校验用户名与密码。失败时抛 UnauthorizedError(401)。

    注意：用户名不存在与密码错误返回同一条提示，避免被用来枚举用户。
    """
    user = db.scalar(select(User).where(User.username == username))
    if user is None or user.is_deleted:
        raise UnauthorizedError("用户名或密码错误")
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误")
    return user
