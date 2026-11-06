"""所有 ORM 模型的基类。Alembic 通过 Base.metadata 收集表结构。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
