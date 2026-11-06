"""add roles and user_roles

第五章产物：新增角色表和多对多关联表,并预置三个角色。

Revision ID: 0002_roles
Revises: 0001_initial
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0002_roles"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False, comment="角色名"),
        sa.Column("description", sa.String(200), nullable=True, comment="角色说明"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        comment="角色表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("role_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        comment="用户-角色关联表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # 预置角色,方便案例直接使用
    op.execute(
        sa.text(
            "INSERT INTO roles (name, description) VALUES "
            "('admin', '管理员,可管理所有资源'), "
            "('editor', '编辑,可改内容不能删用户'), "
            "('viewer', '访客,只读')"
        )
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("roles")
