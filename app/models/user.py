"""User 模型 —— 映射 learn_mysql.users 表。

SQLAlchemy 2.0 风格：`Mapped[T]` 声明 Python 类型，`mapped_column()` 描述数据库列。
两者分离的好处是 IDE 能直接推断 `user.username` 是 str，不用靠约定。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}

    id: Mapped[int] = mapped_column(
        INTEGER(unsigned=True),
        primary_key=True,
        autoincrement=True,
        comment="用户主键",
    )
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="用户名，唯一"
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0.00"),
        comment="账户余额，保留两位小数",
    )
    is_deleted: Mapped[bool] = mapped_column(
        TINYINT(1),
        nullable=False,
        server_default=text("0"),
        comment="软删除标记：0正常，1已删除",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="注册时间",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} balance={self.balance}>"
