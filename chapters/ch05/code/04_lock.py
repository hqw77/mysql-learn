"""第五章 · 案例 4：并发下的「丢更新」,以及 FOR UPDATE 怎么救。

学到什么：
    两个人同时读同一行、各自扣款、各自提交,后提交的会把前一个的修改覆盖掉。
    因为 UPDATE 写的是「我算好的值」,不是「减 300」。
    SELECT ... FOR UPDATE 能把这一行锁住,让第二个事务排队。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch05/code/04_lock.py

注意：案例跑完会把余额恢复原样。
"""

import sys
import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import select  # noqa: E402

from app.db.engine import engine  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

ORIGINAL = Decimal("888.00")


def show(title: str) -> None:
    print(f"\n--- {title} ---")


def reset_balance() -> None:
    with SessionLocal() as db:
        u = db.get(User, 1)
        u.balance = ORIGINAL
        db.commit()


if __name__ == "__main__":
    reset_balance()

    show("① 两个会话同时读到同一个余额")
    db1, db2 = SessionLocal(), SessionLocal()
    try:
        u1 = db1.get(User, 1)
        u2 = db2.get(User, 1)
        print(f"    会话 A 读到: {u1.balance}")
        print(f"    会话 B 读到: {u2.balance}")

        show("② A 先扣 300 并提交")
        u1.balance = u1.balance - Decimal("300.00")
        db1.commit()
        print(f"    A 提交后,库里是: {db1.get(User, 1).balance}")

        show("③ B 也扣 300 并提交（它用的是刚才读到的旧值）")
        u2.balance = u2.balance - Decimal("300.00")     # ⚠️ 基于 888 算的,不知道 A 已经改过
        db2.commit()
        print(f"    B 提交后,库里是: {db2.get(User, 1).balance}")
        print("    正确应该是 888 - 300 - 300 = 288")
        print("    实际成了 588 —— 少了 300,这就是「丢更新」")
    finally:
        db1.close()
        db2.close()

    show("④ 换成加锁读：SELECT ... FOR UPDATE")
    stmt = select(User).where(User.id == 1).with_for_update()
    print("    生成的 SQL:")
    print("     ", " ".join(str(stmt).split()))
    print("    → 结尾多出的 FOR UPDATE 就是加锁")
    print("    效果：B 想读这一行时会阻塞,直到 A 提交——读到的一定是最新值")

    show("⑤ 更稳的写法：让数据库自己算")
    with SessionLocal() as db:
        u = db.get(User, 1)
        u.balance = u.balance - Decimal("300.00")
        db.commit()
        print(f"    ORM 写法生成的是 SET balance = 具体值,所以有丢更新风险")
    reset_balance()
    print(f"    已恢复为 {ORIGINAL}")

    show("结论")
    print("    并发改同一行有三种解法：")
    print("      1. SELECT ... FOR UPDATE（悲观锁,最直接）")
    print("      2. 乐观锁：加 version 列,UPDATE ... WHERE version = 旧值")
    print("      3. 让数据库算：UPDATE users SET balance = balance - 300（原子操作）")
