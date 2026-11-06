"""第四章 · 案例 4：批量写入的差距,以及为什么要有 service 层。

学到什么：
    逐条 commit 是一百次网络往返；add_all + 一次 commit 快一个数量级。
    同一套操作封装进 service 后,调用方只剩一行,且异常已经翻译成业务语义。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch04/code/04_batch_and_service.py
"""

import sys
import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

from sqlalchemy import delete  # noqa: E402

from app.core.exceptions import ConflictError, NotFoundError  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services import user_service  # noqa: E402

ROWS = 100


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    stamp = int(time.time()) % 100000
    prefix = f"bt{stamp}"

    with SessionLocal() as db:
        show(f"① 逐条 commit：{ROWS} 条")
        start = time.perf_counter()
        for i in range(ROWS):
            db.add(User(username=f"{prefix}_a{i}", phone=f"135{stamp}{i:03d}"[:20]))
            db.commit()                      # ⚠️ 每条一次网络往返
        slow = time.perf_counter() - start

        show(f"② add_all + 一次 commit：{ROWS} 条")
        start = time.perf_counter()
        db.add_all([
            User(username=f"{prefix}_b{i}", phone=f"134{stamp}{i:03d}"[:20])
            for i in range(ROWS)
        ])
        db.commit()
        fast = time.perf_counter() - start

        print(f"    逐条 commit : {slow:6.3f}s")
        print(f"    批量 commit : {fast:6.3f}s")
        print(f"    快 {slow / fast:.1f} 倍")

        show("③ 换成 service 层,调用方只写一行")
        user = user_service.create_user(db, f"{prefix}_svc", f"133{stamp}001"[:20], Decimal("50.00"))
        print("    创建:", user)

        fetched = user_service.get_user(db, user.id)
        print("    查询:", fetched)

        updated = user_service.update_balance(db, user.id, Decimal("150.00"))
        print("    改余额:", updated.balance, "（50 + 150）")

        page, total = user_service.list_users(db, page=1, size=3)
        print(f"    分页: 共 {total} 条,本页 {len(page)} 条")

        show("④ service 把数据库异常翻译成了业务异常")
        try:
            user_service.create_user(db, f"{prefix}_svc", f"133{stamp}002"[:20])   # 用户名重复
        except ConflictError as exc:
            print("    ConflictError:", exc, " → 路由层会转成 409")

        try:
            user_service.get_user(db, 99999999)
        except NotFoundError as exc:
            print("    NotFoundError:", exc, " → 路由层会转成 404")

        show("⑤ 清理测试数据")
        db.rollback()
        db.execute(delete(User).where(User.username.like(f"{prefix}%")))
        db.commit()
        print("    已清理")
