"""案例 3：脏检查 —— 改属性到底什么时候才发 UPDATE。

学到什么：
    1. 改属性只打标记,不发 SQL
    2. 赋相同的值,flush 时不会生成 UPDATE
    3. 赋不同的值,UPDATE 只带变化的那一列
    4. rollback 会把内存里的修改一起丢掉

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch03/code/03_dirty_check.py

注意：全程不 commit,最后 rollback,不会改坏你的数据。
"""

import os
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, create_engine, event, select
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engine = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}"
    f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
    f"/{os.getenv('MYSQL_DATABASE', 'learn_mysql')}?charset=utf8mb4",
)

# 把 ORM 实际发出去的 SQL 抓下来
_captured: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, parameters, context, executemany):
    _captured.append(" ".join(statement.split()))


def take_sql() -> list[str]:
    """取出上次清空以来、和 users 表有关的 SQL。"""
    got = [s for s in _captured if "users" in s.lower()]
    _captured.clear()
    return got


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_deleted: Mapped[bool] = mapped_column(TINYINT(1))
    created_at: Mapped[datetime] = mapped_column(DateTime)


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    with Session(engine) as session:
        show("① 只是查询")
        user = session.get(User, 1)
        take_sql()
        print(f"    balance = {user.balance}")
        print(f"    session.dirty = {session.dirty}")

        show("② 赋一个相同的值,然后 flush")
        user.username = user.username
        print(f"    session.dirty = {session.dirty}   ← 对象进去了")
        session.flush()
        sqls = take_sql()
        print(f"    实际发出去的 SQL：{sqls if sqls else '（没有 UPDATE）'}")
        print("    结论：进了 dirty 集合 ≠ 一定会发 UPDATE")

        show("③ 赋一个不同的值,然后 flush")
        user.balance = Decimal("777.00")
        session.flush()
        for s in take_sql():
            print("    SQL:", s)
        print("    结论：只 UPDATE 变化的那一列,不是整行覆盖")

        show("④ rollback 把内存修改一起丢弃")
        print(f"    回滚前（内存里）：{user.balance}")
        session.rollback()
        print(f"    回滚后（重新查）：{session.get(User, 1).balance}")
        print("    数据库里的值从头到尾没变过")
