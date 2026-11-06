"""系统探针。一个查进程,一个查数据库,用来验证分层是否打通。"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    """进程存活探测：不碰数据库,纯内存返回。"""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    """数据库连通探测：走连接池取一条连接执行 SELECT。"""
    version = db.execute(text("SELECT VERSION()")).scalar_one()
    return {"status": "ok", "mysql_version": version}
