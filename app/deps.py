"""FastAPI 依赖集合。router 从这里导入依赖,不直接碰 db 层。"""

from app.db.session import get_db

__all__ = ["get_db"]
