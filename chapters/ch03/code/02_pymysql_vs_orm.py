"""案例 2：同一件事，PyMySQL 和 ORM 各写一遍。

学到什么：
    「发 SQL 拿字典」和「拿对象」到底差在哪。
    答案不在写法，在拿到的东西：一个是 dict，一个是带类型的对象。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch03/code/02_pymysql_vs_orm.py
"""

import os
from datetime import datetime
from decimal import Decimal

import pymysql
from pymysql.cursors import DictCursor
from sqlalchemy import DateTime, Numeric, String, create_engine
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DB = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "learn_mysql"),
    "charset": "utf8mb4",
}

engine = create_engine(
    f"mysql+pymysql://{DB['user']}:{DB['password']}@{DB['host']}:{DB['port']}"
    f"/{DB['database']}?charset={DB['charset']}"
)


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

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} balance={self.balance}>"


if __name__ == "__main__":
    print("=" * 62)
    print("【A】PyMySQL：自己写 SQL，拿回字典")
    print("=" * 62)
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (1,))
            row = cur.fetchone()
        print("SQL       : SELECT * FROM users WHERE id = 1")
        print("返回类型  :", type(row).__name__)
        print("内容      :", row)
        print("怎么取值  : row['username'] =", row["username"])
        print("有没有补全: 没有，键名写错要到运行时才报 KeyError")
    finally:
        conn.close()

    print()
    print("=" * 62)
    print("【B】ORM：不写 SQL，拿回对象")
    print("=" * 62)
    with Session(engine) as session:
        user = session.get(User, 1)
        print("SQL       : 由 ORM 生成，你看不到（echo=True 可以看到）")
        print("返回类型  :", type(user).__name__)
        print("内容      :", user)
        print("怎么取值  : user.username =", user.username)
        print("有没有补全: 有，IDE 能提示 User 的所有属性")

    print()
    print("=" * 62)
    print("【C】关键差别")
    print("=" * 62)
    print(f"{'':<12}{'PyMySQL':<28}{'ORM'}")
    print(f"{'数据载体':<10}{'dict':<28}{'User 实例'}")
    print(f"{'字段类型':<10}{'运行时才知道':<26}{'写代码时就知道'}")
    print(f"{'改数据':<12}{'自己拼 UPDATE':<27}{'user.balance = 100'}")
    print(f"{'复杂查询':<12}{'直接写':<29}{'要绕一层'}")
