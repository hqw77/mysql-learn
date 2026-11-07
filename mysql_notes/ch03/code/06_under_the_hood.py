"""第三章补充：把 SQLAlchemy 的内部过程摊开看。

这个脚本不教你新语法,只做一件事：
每个动作后面,立刻打印「Session 里发生了什么」和「发了什么 SQL」。

跑完你会知道：
    · 什么时候才真正连上数据库
    · add 之后对象去哪了
    · commit 时到底发了什么
    · 改属性为什么不发 SQL
    · 为什么同一个 id 查两次是同一个对象

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python mysql_notes/ch03/code/06_under_the_hood.py
"""

import sys
import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

from sqlalchemy import event, select  # noqa: E402

from app.db.engine import engine  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

# 抓 SQL：每发一条就记下来
_captured: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, parameters, context, executemany):
    _captured.append(" ".join(statement.split()))


def take_sql() -> list[str]:
    """取出上次清空以来执行过的 SQL。"""
    got = list(_captured)
    _captured.clear()
    return got


def show_sql(label: str = "") -> None:
    sqls = [s for s in take_sql() if "users" in s.lower()]
    if sqls:
        for s in sqls:
            print(f"     发出的 SQL: {s[:90]}")
    else:
        print(f"     发出的 SQL: （无）" + (f"  ← {label}" if label else ""))


def hr(text: str) -> None:
    print("\n" + "─" * 72)
    print(text)
    print("─" * 72)


if __name__ == "__main__":
    stamp = int(time.time()) % 100000

    # =================================================================
    hr("① 创建 engine 的时候,连上数据库了吗？")
    print("   engine = create_engine(url)")
    print("   连接池状态:", engine.pool.status())
    take_sql()
    print("   → 没有连接。create_engine 只是准备好参数和池子,一条 SQL 都没发")
    print("     （真正连库是在第一次执行 SQL 的时候）")

    # =================================================================
    hr("② 第一次查库：连接在这里才建立")
    with SessionLocal() as db:
        user = db.get(User, 1)
        print(f"   session.get(User, 1)  →  {user}")
        show_sql()
        print("   连接池状态:", engine.pool.status())
        print("   → 这时候才真正连上 MySQL,并且连接会留在池子里复用")

        # =============================================================
        hr("③ add 一个对象：它去了哪里？")
        take_sql()
        new_user = User(username=f"hood{stamp}", phone=f"132{stamp:08d}", balance=Decimal("0.00"))
        db.add(new_user)
        print(f"   新对象的 id = {new_user.id}   ← 还没有 id")
        print(f"   session.new     = {len(db.new)} 个对象    ← 待插入的")
        print(f"   session.dirty   = {len(db.dirty)} 个对象    ← 被改过的")
        print(f"   session.deleted = {len(db.deleted)} 个对象    ← 待删除的")
        show_sql()
        print("   → add 只是把它登记到 session.new,没有发 SQL")

        # =============================================================
        hr("④ commit：这时候才 INSERT")
        db.commit()
        print(f"   commit 之后 id = {new_user.id}   ← 主键回来了")
        print(f"   session.new     = {len(db.new)} 个对象    ← 清空了")
        show_sql()

        # =============================================================
        hr("⑤ 改一个属性：为什么不发 SQL？")
        take_sql()
        old_balance = new_user.balance
        new_user.balance = Decimal("777.00")
        print(f"   内存里的值 = {new_user.balance}")
        print(f"   session.dirty = {len(db.dirty)} 个对象    ← 它进了脏集合")
        show_sql()
        print("   → 改属性只打了个标记,数据库毫不知情")

        hr("⑥ commit：这时候才 UPDATE,而且只带变化的列")
        db.commit()
        show_sql()
        print(f"   session.dirty = {len(db.dirty)} 个对象    ← 提交后清空")

        # =============================================================
        hr("⑦ identity map：同一个 id 查两次,是同一个对象吗？")
        take_sql()
        a = db.get(User, 2)          # 第一次：这个对象还没加载过,要查库
        b = db.get(User, 2)          # 第二次：已经在 session 里了,不再查
        same = [s for s in _captured if "users" in s.lower()]
        print(f"   a = db.get(User, 2)   →  {a}")
        print(f"   b = db.get(User, 2)   →  {b}")
        print(f"   a is b ?  {a is b}")
        print(f"   这两次 get 一共发了 {len(same)} 条 SQL")
        take_sql()
        print("   → 第二次没有再查库,直接从 session 缓存里拿的")
        print("     这叫 identity map：一个 Session 里,一个 id 只对应一个对象")

        # =============================================================
        hr("⑧ rollback：改了不提交,会发生什么")
        user1 = db.get(User, 1)
        before = user1.balance
        user1.balance = Decimal("1.00")
        print(f"   内存里改成 {user1.balance},数据库里还是 {before}")
        db.rollback()
        take_sql()
        print(f"   rollback 之后重新查：{db.get(User, 1).balance}")
        print("   → 没提交的修改被丢弃了")

        # =============================================================
        hr("⑨ 清理测试数据")
        db.delete(db.get(User, new_user.id))
        db.commit()
        take_sql()
        print("   已删除本次创建的用户")

    print("\n" + "=" * 72)
    print("跑完这九步,你已经看见 SQLAlchemy 的全部「魔法」了：")
    print("  1. engine 只是配置,第一次执行 SQL 才连库")
    print("  2. add 只登记,commit 才 INSERT")
    print("  3. 改属性只打标记,commit 才 UPDATE,且只带变化的列")
    print("  4. 同 id 只查一次,之后从 session 缓存拿")
    print("  5. rollback 丢弃未提交的修改")
    print("=" * 72)
