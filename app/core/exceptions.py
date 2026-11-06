"""业务异常。service 层抛出,由全局处理器统一转成 HTTP 响应。"""


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message, status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str = "资源冲突") -> None:
        super().__init__(message, status_code=409)


class UnauthorizedError(AppError):
    """未登录、令牌无效或已过期。"""

    def __init__(self, message: str = "未认证") -> None:
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    """已登录但没有权限。"""

    def __init__(self, message: str = "没有权限") -> None:
        super().__init__(message, status_code=403)
