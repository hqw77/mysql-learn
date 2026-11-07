"""第四章 · 案例 1：新增一条数据,以及唯一键冲突长什么样。

学到什么：
    add() 只是把对象放进 Session 的 new 集合；commit() 才真的 INSERT。
    commit 之后 refresh() 才能拿到数据库生成的 created_at。
    用户名/手机号重复时,错误在 commit 那一刻才炸,抛 IntegrityError。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python mysql_notes/ch04/code/01_add.py
"""

import sys
import time
from pathlib import Path

# 让脚本能从仓库根目录 import app 包（文件在 mysql_notes/ch04/code/,往上三级是仓库根）
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

STAMP = int(time.time() * 1000) % 10_000_000


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    name = f"u{STAMP}"
    phone = f"139{STAMP:08d}"[:20]

    with SessionLocal() as db:
        show("① 新建一个对象,add 之后还没提交")
        user = User(username=name, phone=phone, balance=0)
        db.add(user)
        print("    user.id =", user.id, "  ← 还没 INSERT,主键是空的")
        print("    session.new 里有它吗:", len(db.new), "个  ← add 之后才进 new 集合")

        show("② commit 之后")
        db.commit()
        print("    user.id =", user.id)

        show("③ refresh 才能看到数据库填的默认值")
        print("    created_at =", user.created_at, "  ← server_default 填的")
        print("    balance    =", user.balance, "  ← DEFAULT 0.00 生效")

        show("④ 再插一个同名用户会怎样")
        dup = User(username=name, phone=f"138{STAMP:08d}"[:20], balance=0)
        db.add(dup)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()                     # ⚠️ 出错必须 rollback,否则 Session 卡在坏事务里
            msg = str(exc.orig)
            print("    捕获 IntegrityError:", msg[:60], "...")
            print("    → 业务层要把它翻译成 409")

        show("⑤ 清理本次测试数据")
        db.delete(db.get(User, user.id))
        db.commit()
        print("    已删除,库恢复原样")
