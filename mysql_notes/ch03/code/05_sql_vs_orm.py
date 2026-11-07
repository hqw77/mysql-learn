"""第三章补充：同一个操作,用 SQL 写一遍、用 ORM 写一遍,并排对比。

这个脚本不教新东西,只做一件事：把你已经会的 SQL,和等价的 ORM 写法摆在一起看。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python mysql_notes/ch03/code/05_sql_vs_orm.py
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

import pymysql  # noqa: E402
from pymysql.cursors import DictCursor  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

DB = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "learn_mysql"),
    "charset": "utf8mb4",
}


def sql_query(sql: str, params=None):
    """用原生 SQL 查,返回字典列表。"""
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def title(text: str) -> None:
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


if __name__ == "__main__":
    # ---------------------------------------------------------------
    title("① 查一条：SELECT ... WHERE id = 1")

    print("\n[SQL]")
    print("  SELECT * FROM users WHERE id = 1")
    row = sql_query("SELECT * FROM users WHERE id = %s", (1,))[0]
    print("  结果：", {k: row[k] for k in ("id", "username", "balance")})
    print("  类型：", type(row).__name__)

    print("\n[ORM]")
    print("  session.get(User, 1)")
    with SessionLocal() as db:
        user = db.get(User, 1)
        print("  结果：", user)
        print("  类型：", type(user).__name__)
    print("\n  → 拿到的东西不一样：一个是字典,一个是对象")

    # ---------------------------------------------------------------
    title("② 按条件查：SELECT ... WHERE balance > 200")

    print("\n[SQL]")
    print("  SELECT username, balance FROM users WHERE balance > 200 ORDER BY balance DESC")
    rows = sql_query(
        "SELECT username, balance FROM users WHERE balance > 200 ORDER BY balance DESC"
    )
    for r in rows:
        print(f"    {r['username']}  {r['balance']}")

    print("\n[ORM]")
    print("  select(User).where(User.balance > 200).order_by(User.balance.desc())")
    with SessionLocal() as db:
        users = db.scalars(
            select(User).where(User.balance > 200).order_by(User.balance.desc())
        ).all()
        for u in users:
            print(f"    {u.username}  {u.balance}")
    print("\n  → 同样的查询,只是把 SQL 关键字换成了方法名")
    print("    WHERE → .where()   ORDER BY → .order_by()   SELECT → select()")

    # ---------------------------------------------------------------
    title("③ 计数：SELECT COUNT(*)")

    print("\n[SQL]")
    print("  SELECT COUNT(*) AS n FROM users")
    print("  结果：", sql_query("SELECT COUNT(*) AS n FROM users")[0]["n"])

    print("\n[ORM]")
    print("  select(func.count()).select_from(User)")
    with SessionLocal() as db:
        n = db.scalar(select(func.count()).select_from(User))
        print("  结果：", n)
    print("\n  → func.count() 就是 SQL 里的 COUNT(*)")

    # ---------------------------------------------------------------
    title("④ 改数据：UPDATE ... WHERE id = 1（演示完会回滚）")

    print("\n[SQL]")
    print("  UPDATE users SET balance = 999 WHERE id = 1")
    print("  → 你要自己拼字符串,自己 commit,自己处理参数")

    print("\n[ORM]")
    print("  user.balance = 999")
    print("  session.commit()")
    with SessionLocal() as db:
        u = db.get(User, 1)
        before = u.balance
        u.balance = Decimal("999.00")
        print(f"  改完还没提交,内存里是 {u.balance},数据库里还是 {before}")
        db.rollback()
        print(f"  回滚后重新查：{db.get(User, 1).balance}")
    print("\n  → 改属性不发 SQL,commit 才发；这就是第三章讲的脏检查")

    # ---------------------------------------------------------------
    title("⑤ 对照表：SQL 关键字 ↔ ORM 写法")

    mapping = [
        ("SELECT * FROM users", "select(User)"),
        ("WHERE id = 1", "session.get(User, 1)"),
        ("WHERE balance > 200", ".where(User.balance > 200)"),
        ("ORDER BY balance DESC", ".order_by(User.balance.desc())"),
        ("LIMIT 2", ".limit(2)"),
        ("OFFSET 2", ".offset(2)"),
        ("COUNT(*)", "func.count()"),
        ("INSERT INTO ...", "db.add(User(...)) 然后 commit()"),
        ("UPDATE ... SET", "user.字段 = 新值 然后 commit()"),
        ("DELETE FROM ...", "db.delete(user) 然后 commit()"),
    ]
    print(f"\n  {'SQL 里写的':<28}{'ORM 里写的'}")
    print("  " + "-" * 66)
    for sql, orm in mapping:
        print(f"  {sql:<28}{orm}")

    print("\n  一句话：ORM 没有发明新东西,它只是把 SQL 的关键字变成了方法名。")
