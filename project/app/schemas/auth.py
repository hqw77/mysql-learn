"""认证相关的数据结构。"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    """注册入参。密码只在前端到后端这一路上出现一次，之后只存哈希。"""

    username: str = Field(min_length=2, max_length=50, description="用户名,2~50 字符")
    phone: str = Field(pattern=r"^1\d{10}$", description="手机号,11 位,1 开头")
    password: str = Field(min_length=6, max_length=64, description="密码,6~64 字符")


class LoginIn(BaseModel):
    """登录入参。"""

    username: str = Field(description="用户名")
    password: str = Field(description="明文密码")


class TokenOut(BaseModel):
    """登录成功后的令牌。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="有效期(秒)")


class CurrentUserOut(BaseModel):
    """当前登录用户的信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    balance: Decimal
    roles: list[str] = []
