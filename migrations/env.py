"""Alembic 运行环境。

连接串不写在 alembic.ini 里，而是从 app.core.config 读取，
这样密码只需要维护 .env 一份。
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  —— 必须导入，模型才会注册到 Base.metadata
from app.core.config import settings
from app.db.base import Base

config = context.config

# 密码里的 % 会被 configparser 当成插值符号，必须转义成 %%
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """只让 Alembic 管理"模型里定义过"的对象。

    库里还躺着一批第一章的练习表（authors/books/orders/big_users…），
    它们没有对应的 ORM 模型。不加这层过滤，autogenerate 会把它们
    统统判成"该删除"，生成一堆 DROP TABLE。

    reflected=True 且 compare_to=None 的含义是：数据库里有、模型里没有。
    """
    if reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL，不连数据库。"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连库执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
