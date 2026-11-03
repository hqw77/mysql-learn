"""Session 工厂与 FastAPI 依赖。

Engine 管"连接"，Session 管"一次工作单元"。一个请求一个 Session。
"""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.engine import engine

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """每请求一个 Session，用完必关。

    用 yield：请求正常返回或抛异常，finally 都会执行，连接一定归还连接池。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
