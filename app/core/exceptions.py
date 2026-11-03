"""业务异常。service 层抛出，由全局处理器统一转成 HTTP 响应。"""


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
