"""应用入口。启动方式：uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.engine import engine
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：以后在这里做连接池预热、缓存加载
    yield
    # 关闭：释放连接池，避免进程退出时连接悬空
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """把业务异常统一映射成 {"detail": "..."} + 对应的状态码。"""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
