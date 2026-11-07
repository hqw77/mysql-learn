"""FastAPI 依赖集合。router 从这里导入依赖,不直接碰 db 层。

除了数据库会话,这里还提供两个鉴权依赖：
    get_current_user  从请求头里取令牌,解析出当前用户
    require_role      要求当前用户具备某个角色
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

# auto_error=False：没带令牌时不抛框架默认错误,交给下面的函数统一处理
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization: Bearer <token> 中解析当前用户。

    令牌缺失、无效、过期,或用户不存在时,统一返回 401。
    """
    if credentials is None:
        raise UnauthorizedError("缺少访问令牌")

    try:
        user_id = decode_access_token(credentials.credentials)
    except PyJWTError:
        raise UnauthorizedError("令牌无效或已过期")

    user = db.get(User, user_id)
    if user is None or user.is_deleted:
        raise UnauthorizedError("用户不存在或已注销")
    return user


def require_role(*role_names: str):
    """生成一个"要求具备指定角色之一"的依赖。

    用法：@router.post(..., dependencies=[Depends(require_role("admin"))])
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        owned = {role.name for role in current_user.roles}
        if not owned & set(role_names):
            raise ForbiddenError(f"需要角色之一：{', '.join(role_names)}")
        return current_user

    return checker


__all__ = ["get_db", "get_current_user", "require_role"]
