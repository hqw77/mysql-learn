"""数据库引擎：全进程只创建一个 Engine，它内部持有连接池。"""

from sqlalchemy import create_engine

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,                     # 每次取连接先探活，避免用到已被 MySQL 断掉的连接
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_timeout=settings.db_pool_timeout,
    echo=settings.db_echo,
)
