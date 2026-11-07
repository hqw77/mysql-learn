"""add password_hash to users

第七章产物：给用户表加密码哈希字段。

已有用户没有密码,因此给一个空字符串默认值；这些用户需要用注册接口
重新创建,或者由管理员重置密码。

Revision ID: 0003_password
Revises: 0002_roles
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_password"
down_revision = "0002_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(255),
            nullable=False,
            server_default=sa.text("''"),
            comment="密码哈希,不存明文",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
