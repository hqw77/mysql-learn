"""第四章 · 案例 2：条件查询、排序、分页。

学到什么：
    分页不是拿全部再切片，而是让数据库 LIMIT/OFFSET；
    总数要单独 COUNT，别用 len(rows) 冒充。
    select() 是 2.0 的写法，session.query() 是 1.x 遗留。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch04/code/02_query.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    with SessionLocal() as db:
        show("① 总共有多少条")
        total = db.scalar(select(func.count()).select_from(User))
        print("    COUNT(*) =", total)

        show("② 条件查询：余额 > 200，按余额倒序")
        stmt = (
            select(User)
            .where(User.balance > 200)
            .order_by(User.balance.desc())
        )
        for u in db.scalars(stmt):
            print("   ", u)

        show("③ 分页：第 1 页，每页 2 条")
        page, size = 1, 2
        stmt = (
            select(User)
            .order_by(User.id)
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = db.scalars(stmt).all()
        page1_count = len(rows)
        print(f"    SELECT ... LIMIT {size} OFFSET {(page - 1) * size}")
        for u in rows:
            print("   ", u)

        show("④ 第 2 页")
        page = 2
        stmt = stmt.offset((page - 1) * size)
        for u in db.scalars(stmt):
            print("   ", u)

        show("⑤ 只取需要的列，别 SELECT *")
        rows = db.execute(select(User.username, User.balance).limit(3)).all()
        for name, balance in rows:
            print(f"    {name:<8} {balance}")

        show("⑥ count 和 len 的区别")
        print("    总数（COUNT）      :", total)
        print("    当页条数（len）    :", page1_count, "  ← 只是这一页，不是总数")
