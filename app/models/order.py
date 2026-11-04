"""Order 模型 —— 映射 learn_mysql.orders。演示「一对多」的「多」这一端。

⚠️ 注意这里没有用 ForeignKey：
   库里 orders.user_id 是逻辑外键，没有物理外键约束（第一章讲过，
   互联网项目通常不在数据库层加外键，避免锁竞争和分库分表麻烦）。
   所以关系映射要用 primaryjoin + foreign() 显式告诉 SQLAlchemy「哪边是外键」。
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Numeric, String, text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"comment": "订单主表"}

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, comment="订单号")
    user_id: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, comment="下单用户ID")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="订单总金额")
    status: Mapped[int] = mapped_column(
        TINYINT, nullable=False, server_default=text("0"), comment="状态：0待支付，1已支付，2已发货"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    # 💡 foreign() 声明「Order.user_id 是外键那一侧」，替代缺失的 FK 约束
    user: Mapped["User"] = relationship(
        primaryjoin="foreign(Order.user_id) == User.id",
        back_populates="orders",
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} no={self.order_no!r} amount={self.total_amount}>"
