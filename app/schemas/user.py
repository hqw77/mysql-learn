"""Pydantic 模型：定义「接口收什么、返什么」,与 ORM 模型解耦。

为什么要单独一层：
    ORM 模型描述数据库,Pydantic 模型描述 API。
    两者混用会把「手机号格式校验」这种接口规则写进表结构层,
    也会让响应里意外带出 password 之类的字段。
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """注册/创建用户的入参。"""

    username: str = Field(min_length=2, max_length=50, description="用户名,2~50 字符")
    phone: str = Field(pattern=r"^1\d{10}$", description="手机号,11 位,1 开头")
    balance: Decimal = Field(default=Decimal("0.00"), ge=0, description="初始余额,不能为负")


class UserUpdateBalance(BaseModel):
    """调整余额的入参。amount 可正可负。"""

    amount: Decimal = Field(description="调整金额,正数加、负数减")


class UserOut(BaseModel):
    """返回给前端的用户结构。⚠️ 这里决定了哪些字段能暴露出去。"""

    # 💡 from_attributes=True 让 Pydantic 能直接吃 ORM 对象：UserOut.model_validate(user)
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    phone: str
    balance: Decimal
    is_deleted: bool
    created_at: datetime


class UserPage(BaseModel):
    """分页响应：数据和分页元信息放在一起。"""

    total: int
    page: int
    size: int
    items: list[UserOut]
