"""第五章 · 案例 1：一对多关系 —— 一个用户多张订单。

学到什么：
    relationship 让你从对象直接走到关联对象：user.orders 是一组 Order。
    默认是「懒加载」：访问 user.orders 的那一刻才发 SELECT,不是查 User 时一起查。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch05/code/01_relationship.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

from sqlalchemy import event, select  # noqa: E402

from app.db.engine import engine  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Order, User  # noqa: E402

_captured: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, parameters, context, executemany):
    _captured.append(" ".join(statement.split()))


def take_sql() -> list[str]:
    got = [s for s in _captured if "orders" in s.lower() or "users" in s.lower()]
    _captured.clear()
    return got


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    with SessionLocal() as db:
        show("① 先查用户（此时不会碰 orders 表）")
        user = db.get(User, 1)
        print("    user:", user)
        print("    这一步的 SQL:", take_sql() or "（无）")

        show("② 访问 user.orders —— 懒加载这时候才发 SQL")
        orders = user.orders
        print("    订单数:", len(orders))
        for o in orders:
            print("   ", o)
        for s in take_sql():
            print("    懒加载发出的 SQL:", s[:100])

        show("③ 反向走：从订单找到用户")
        order = db.get(Order, 1)
        print("    order:", order)
        print("    它的用户:", order.user.username)
        take_sql()

        show("④ 用 SQL 直接做关联查询（join）,一次拿完")
        rows = db.execute(
            select(User.username, Order.order_no, Order.total_amount)
            .join(Order, Order.user_id == User.id)     # ⚠️ 没有物理外键,join 条件要自己写
            .order_by(Order.id)
        ).all()
        for name, no, amount in rows:
            print(f"    {name:<6} {no:<8} {amount}")

        show("⑤ 给某个用户加一张订单（走关系,不用手写 user_id）")
        new_order = Order(order_no="ORD900", total_amount=88)
        user.orders.append(new_order)          # 💡 由关系自动填 user_id
        db.commit()
        print("    新增订单:", new_order)
        print("    用户现在的订单数:", len(user.orders))
        print("    它的 user_id 被自动设成:", new_order.user_id)

        show("⑥ 清理本次测试订单")
        db.delete(db.get(Order, new_order.id))
        db.commit()
        db.expire_all()                        # 丢掉缓存,重新从库里读
        print("    已清理,订单数恢复:", len(db.get(User, 1).orders))
