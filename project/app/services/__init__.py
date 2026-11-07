"""业务逻辑层：一个模块一类资源,事务边界在函数内部。

路由层只调用这里,不直接碰 Session。
"""

from app.services import auth_service, user_service

__all__ = ["auth_service", "user_service"]
