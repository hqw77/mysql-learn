"""安全相关的工具：密码哈希与 JWT 令牌。

两个原则：
    1. 密码只存哈希，永远不存明文，也不可逆；
    2. 令牌只存签名后的字符串，服务端不保存会话状态。
"""

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# argon2 自带盐值，同一密码每次哈希结果都不同
_hasher = PasswordHasher()


def hash_password(raw: str) -> str:
    """把明文密码转成哈希字符串。"""
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """校验明文密码是否匹配哈希。哈希为空或不合法时返回 False。"""
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int) -> str:
    """签发令牌。payload 里只放用户 id 和过期时间。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    """校验令牌并取出用户 id。签名错误或过期时抛 jwt.PyJWTError。"""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])
