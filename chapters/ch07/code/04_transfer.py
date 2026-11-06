"""第七章 · 案例 4：转账 —— 事务实战。

学到什么：
    转账要改两行数据，必须在一个事务里：要么都成功，要么都回滚。
    余额不足时抛业务异常，两边余额都不能变。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch07/code/04_transfer.py
"""

import sys
import time
import warnings
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project"))

warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

STAMP = int(time.time()) % 100000


def show(title: str) -> None:
    print(f"\n--- {title} ---")


def balance_of(uid: int) -> Decimal:
    with SessionLocal() as db:
        return db.get(User, uid).balance


if __name__ == "__main__":
    with TestClient(app) as client:
        # 准备两个用户
        users = {}
        for who, phone_prefix, balance in (("甲", "135", "500.00"), ("乙", "136", "100.00")):
            name = f"tf{STAMP}{phone_prefix}"
            r = client.post(
                "/auth/register",
                json={"username": name, "phone": f"{phone_prefix}{STAMP:08d}", "password": "secret123"},
            )
            uid = r.json()["id"]
            # 注册接口不开放余额设置，直接改库（模拟"已有余额"）
            with SessionLocal() as db:
                u = db.get(User, uid)
                u.balance = Decimal(balance)
                db.commit()
            users[who] = (uid, name)

        (a_id, a_name), (b_id, b_name) = users["甲"], users["乙"]

        r = client.post("/auth/login", json={"username": a_name, "password": "secret123"})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        show("① 初始余额")
        print(f"    甲({a_id}): {balance_of(a_id)}")
        print(f"    乙({b_id}): {balance_of(b_id)}")

        show("② 甲给乙转 200 → 200")
        r = client.post("/transfer", json={"to_user_id": b_id, "amount": "200.00"}, headers=headers)
        print("    状态码:", r.status_code)
        print("    响应:", r.json())
        print(f"    甲的余额: {balance_of(a_id)}   乙的余额: {balance_of(b_id)}")

        show("③ 甲再转 1000（余额不足）→ 400，且两边都不变")
        before_a, before_b = balance_of(a_id), balance_of(b_id)
        r = client.post("/transfer", json={"to_user_id": b_id, "amount": "1000.00"}, headers=headers)
        print("    状态码:", r.status_code, " 响应:", r.json())
        print(f"    甲: {before_a} → {balance_of(a_id)}")
        print(f"    乙: {before_b} → {balance_of(b_id)}")
        print("    → 业务校验失败时根本没进 UPDATE，两边余额纹丝不动")

        show("④ 不带令牌转账 → 401")
        r = client.post("/transfer", json={"to_user_id": b_id, "amount": "1.00"})
        print("    状态码:", r.status_code, " 响应:", r.json())

        show("⑤ 清理测试数据")
        with SessionLocal() as db:
            for uid in (a_id, b_id):
                u = db.get(User, uid)
                if u is not None:
                    db.delete(u)
            db.commit()
        print("    已清理")
