"""第四章 · 案例 3：改数据的两写法,删数据的两种取舍。

学到什么：
    改单个对象 → 直接改属性,脏检查生成 UPDATE；
    批量改 → 用 update() 语句,一条 SQL 改一批；
    删数据 → 软删（is_deleted=1）保留行,硬删（DELETE）不可恢复。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch04/code/03_update_delete.py
"""

import sys
import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

from sqlalchemy import delete, event, select, update  # noqa: E402

from app.db.engine import engine  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

_captured: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, parameters, context, executemany):
    _captured.append(" ".join(statement.split()))


def take_sql() -> list[str]:
    got = [s for s in _captured if "users" in s.lower()]
    _captured.clear()
    return got


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    stamp = int(time.time()) % 100000
    prefix = f"up{stamp}"

    with SessionLocal() as db:
        show("① 先造 3 条测试数据")
        db.add_all([
            User(username=f"{prefix}_{i}", phone=f"136{stamp}{i:02d}"[:20], balance=Decimal("100.00"))
            for i in range(3)
        ])
        db.commit()
        take_sql()
        users = db.scalars(select(User).where(User.username.like(f"{prefix}%")).order_by(User.id)).all()
        for u in users:
            print("   ", u)

        show("② 改单个对象：只改属性,commit 时发 UPDATE")
        target = users[0]
        target.balance = Decimal("888.00")
        db.commit()
        for s in take_sql():
            print("    SQL:", s)
        print("    → 只改了 balance 一列")

        show("③ 批量改：一条 SQL 改一批")
        result = db.execute(
            update(User).where(User.username.like(f"{prefix}%")).values(balance=0)
        )
        db.commit()
        for s in take_sql():
            print("    SQL:", s)
        print("    影响行数:", result.rowcount)

        show("④ 软删除：行还在,只是标记")
        victim = users[1]
        victim.is_deleted = 1
        db.commit()
        take_sql()
        still_there = db.get(User, victim.id)
        print(f"    is_deleted = {still_there.is_deleted},行仍然存在：{still_there}")
        print("    业务查询要自己过滤：WHERE is_deleted = 0")

        show("⑤ 硬删除：真的没了")
        db.execute(delete(User).where(User.id == users[2].id))
        db.commit()
        take_sql()
        print("    再查:", db.get(User, users[2].id), "  ← None")

        show("⑥ 清理测试数据")
        db.execute(delete(User).where(User.username.like(f"{prefix}%")))
        db.commit()
        print("    已清理")

    show("软删 vs 硬删怎么选")
    print("    软删：用户可恢复、要留审计、有关联外键不能断 —— 用户表几乎都用这个")
    print("    硬删：日志、临时数据、明确要求删除（合规）——  才用这个")
