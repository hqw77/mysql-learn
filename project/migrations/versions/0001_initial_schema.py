"""initial schema: users

把库中已存在的 users 表固化成第一个迁移版本。
因为表已经在库里,这份迁移只需 `alembic stamp head` 标记为已执行,
不要真的 upgrade（会撞 Table already exists）。

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            mysql.INTEGER(unsigned=True),
            autoincrement=True,
            nullable=False,
            comment="用户主键",
        ),
        sa.Column("username", sa.String(50), nullable=False, comment="用户名,唯一"),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column(
            "balance",
            sa.Numeric(10, 2),
            server_default=sa.text("0.00"),
            nullable=False,
            comment="账户余额,保留两位小数",
        ),
        sa.Column(
            "is_deleted",
            mysql.TINYINT(1),
            server_default=sa.text("0"),
            nullable=False,
            comment="软删除标记：0正常,1已删除",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="注册时间",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("phone"),
        comment="用户表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    op.drop_table("users")
