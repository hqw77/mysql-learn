"""应用配置：所有可调参数集中在此,从 .env 或系统环境变量读取。

优先级：环境变量 > .env 文件 > 这里的默认值。
"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

# project/ 目录：config.py 在 project/app/core/ 下,往上三层
PROJECT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",     # 💡 用绝对路径,从任何工作目录运行都能读到
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "python-backend-notes"
    debug: bool = True

    # ---- 认证 ----
    jwt_secret: str = "dev-secret-change-me-please-0123456789"   # ⚠️ 生产环境必须换成随机长字符串(≥32 字节)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ---- 数据库连接 ----
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "learn_mysql"
    mysql_charset: str = "utf8mb4"

    # ---- 连接池 ----
    db_pool_size: int = 5          # 常驻连接数
    db_max_overflow: int = 10      # 高峰期允许临时超出的连接数
    db_pool_recycle: int = 3600    # 连接存活多少秒后强制回收（避开 MySQL wait_timeout）
    db_pool_timeout: int = 30      # 池满时等待可用连接的超时秒数
    db_echo: bool = False          # True 会打印每条 SQL,调试用

    @property
    def database_url(self) -> str:
        """拼出 SQLAlchemy 连接串。

        密码必须 URL 编码,否则含 @ : / # 的密码会把连接串截断。
        """
        return (
            f"mysql+pymysql://{self.mysql_user}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )


@lru_cache
def get_settings() -> Settings:
    """带缓存的配置读取,全进程只解析一次 .env。"""
    return Settings()


settings = get_settings()
