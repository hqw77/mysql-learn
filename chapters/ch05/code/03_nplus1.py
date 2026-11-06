"""第五章 · 案例 3：N+1 查询 —— 关系映射最容易踩的性能坑。

学到什么：
    懒加载下,N 个用户就要发 1 + N 条 SQL；
    selectinload 只发 2 条（1 条查用户,1 条 IN 查所有订单）,与 N 无关。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch05/code/03_nplus1.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import event, select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.db.engine import engine  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

_captured: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, parameters, context, executemany):
    _captured.append(" ".join(statement.split()).lower())


def reset() -> None:
    _captured.clear()


def count_users_sql() -> int:
    return len([s for s in _captured if s.startswith("select") and "from users" in s])


def count_orders_sql() -> int:
    return len([s for s in _captured if "from orders" in s])


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    show("① 懒加载：访问 user.orders 时逐个发 SQL")
    with SessionLocal() as db:
        reset()
        users = db.scalars(select(User)).all()
        for u in users:
            _ = len(u.orders)          # ⚠️ 每访问一次,就多一条 SQL
        print(f"    用户数: {len(users)}")
        print(f"    'from users' 的 SELECT: {count_users_sql()} 条")
        print(f"    'from orders' 的 SELECT: {count_orders_sql()} 条")
        print(f"    合计 {count_users_sql() + count_orders_sql()} 条 —— 这就是 N+1")

    show("② selectinload：预先加载关联,只多一条 SQL")
    with SessionLocal() as db:
        reset()
        users = db.scalars(select(User).options(selectinload(User.orders))).all()
        for u in users:
            _ = len(u.orders)          # 💡 已经在内存里,不会再发 SQL
        print(f"    用户数: {len(users)}")
        print(f"    'from users' 的 SELECT: {count_users_sql()} 条")
        print(f"    'from orders' 的 SELECT: {count_orders_sql()} 条")
        print(f"    合计 {count_users_sql() + count_orders_sql()} 条 —— 与用户数无关")

    show("③ 两种加载策略对比")
    print("    懒加载 lazy='select'     : 用的时候才查,1 + N 条")
    print("    selectinload            : 先查主表,再用 IN 查关联表,1 + 1 条  ← 最常用")
    print("    joinedload              : 一条 JOIN 查完,1 条,但数据可能重复膨胀")
    print("    raise / noload          : 禁止懒加载,提前暴露问题")

    show("④ 什么时候该用哪个")
    print("    列表页要显示关联信息      → selectinload")
    print("    一对一、且一定要用        → joinedload")
    print("    关联数据很大、不一定用    → 就用懒加载,但要小心循环里的 N+1")
