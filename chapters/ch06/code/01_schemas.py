"""第六章 · 案例 1：Pydantic 校验 —— 请求还没到业务层就被挡下来。

学到什么：
    schema 管「格式对不对」,service 管「业务允不允许」。
    校验失败时 FastAPI 自动返回 422,你一行 if 都不用写。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch06/code/01_schemas.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

from decimal import Decimal  # noqa: E402

from pydantic import ValidationError  # noqa: E402

from app.schemas.user import UserCreate  # noqa: E402


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    show("① 合法数据：直接构造成功")
    ok = UserCreate(username="张三丰", phone="13800000001", balance=Decimal("100.00"))
    print("    对象:", ok)
    print("    转 dict:", ok.model_dump())

    show("② 用户名太短（min_length=2）")
    try:
        UserCreate(username="张", phone="13800000001")
    except ValidationError as exc:
        for e in exc.errors():
            print(f"    字段 {e['loc'][0]}: {e['msg']}")

    show("③ 手机号格式不对（pattern ^1\\d{10}$）")
    try:
        UserCreate(username="张三丰", phone="12345")
    except ValidationError as exc:
        for e in exc.errors():
            print(f"    字段 {e['loc'][0]}: {e['msg']}")

    show("④ 余额为负（ge=0）")
    try:
        UserCreate(username="张三丰", phone="13800000001", balance=Decimal("-1"))
    except ValidationError as exc:
        for e in exc.errors():
            print(f"    字段 {e['loc'][0]}: {e['msg']}")

    show("⑤ 不传 balance 会怎样")
    default = UserCreate(username="张三丰", phone="13800000001")
    print("    balance 默认值:", default.balance, "  ← Field(default=...) 生效")

    show("小结")
    print("    schema 层能挡住：类型错、长度错、格式错、范围错")
    print("    schema 层挡不住：用户名重复、余额不足 —— 那是 service 的事")
