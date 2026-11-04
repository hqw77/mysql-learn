"""Role 模型 + user_roles 关联表 —— 演示「多对多」。

多对多必须有一张中间表，存两边的 id。
这里 user_roles 是新表，由 Alembic 迁移创建（见 migrations/versions/0002_*）。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, text
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# 中间表：只有两个外键，联合主键保证「同一个用户不会有同一个角色两次」
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", INTEGER(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", INTEGER(unsigned=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    comment="用户-角色关联表",
)


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"comment": "角色表"}

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="角色名")
    description: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="角色说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        secondary=user_roles,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r}>"
