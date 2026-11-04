"""模型包。

新增模型后必须在这里导出一次，否则模型不会注册到 Base.metadata，
Alembic 就发现不了它。
"""

from app.models.user import User

__all__ = ["User"]
