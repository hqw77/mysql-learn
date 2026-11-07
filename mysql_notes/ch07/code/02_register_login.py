"""第七章 · 案例 2：注册与登录。

学到什么：
    注册：201；用户名重复：409；登录成功：200 + 令牌；密码错误：401。
    错误提示不区分"用户不存在"和"密码错误",避免被用来枚举账号。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python mysql_notes/ch07/code/02_register_login.py
"""

import sys
import time
import warnings
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


if __name__ == "__main__":
    username = f"reg{STAMP}"
    phone = f"130{STAMP:08d}"
    password = "secret123"

    with TestClient(app) as client:
        show("① 注册 → 201")
        r = client.post(
            "/auth/register",
            json={"username": username, "phone": phone, "password": password},
        )
        print("    状态码:", r.status_code)
        body = r.json()
        print("    响应:", {k: body[k] for k in ("id", "username", "phone")})
        print("    响应里有 password 吗:", "password" in body, "  ← 响应模型已裁剪")
        user_id = body["id"]

        show("② 用同一个用户名再注册 → 409")
        r = client.post(
            "/auth/register",
            json={"username": username, "phone": f"139{STAMP:08d}", "password": password},
        )
        print("    状态码:", r.status_code, " 响应:", r.json())

        show("③ 密码太短 → 422（schema 拦下）")
        r = client.post(
            "/auth/register",
            json={"username": f"x{STAMP}", "phone": f"138{STAMP:08d}", "password": "123"},
        )
        print("    状态码:", r.status_code)
        print("    错误:", r.json()["detail"][0]["msg"])

        show("④ 登录 → 200 + 令牌")
        r = client.post("/auth/login", json={"username": username, "password": password})
        print("    状态码:", r.status_code)
        token = r.json()["access_token"]
        print("    令牌前 40 字符:", token[:40], "...")
        print("    有效期(秒):", r.json()["expires_in"])

        show("⑤ 密码错误 → 401（提示不区分原因）")
        r = client.post("/auth/login", json={"username": username, "password": "wrong-pass"})
        print("    状态码:", r.status_code, " 响应:", r.json())

        r = client.post("/auth/login", json={"username": f"nobody{STAMP}", "password": "whatever"})
        print("    用户名不存在  :", r.status_code, " 响应:", r.json())
        print("    → 两条提示完全一样,攻击者无法判断账号是否存在")

        show("⑥ 清理测试数据")
        with SessionLocal() as db:
            u = db.get(User, user_id)
            if u is not None:
                db.delete(u)
                db.commit()
        print("    已清理")
