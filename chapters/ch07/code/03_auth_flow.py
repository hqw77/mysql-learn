"""第七章 · 案例 3：带令牌访问，以及角色权限。

学到什么：
    不带令牌 → 401；令牌无效 → 401；已登录但角色不够 → 403。
    401 是"你是谁我不知道"，403 是"我知道你是谁，但你不能干这个"。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch07/code/03_auth_flow.py
"""

import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User, user_roles  # noqa: E402

STAMP = int(time.time()) % 100000


def show(title: str) -> None:
    print(f"\n--- {title} ---")


def grant_admin(user_id: int) -> None:
    """直接改数据库授予 admin（正常流程需要另一个管理员来授权）。"""
    with SessionLocal() as db:
        user = db.get(User, user_id)
        admin = db.scalar(select(Role).where(Role.name == "admin"))
        if admin not in user.roles:
            user.roles.append(admin)
            db.commit()


if __name__ == "__main__":
    name = f"auth{STAMP}"

    with TestClient(app) as client:
        r = client.post(
            "/auth/register",
            json={"username": name, "phone": f"133{STAMP:08d}", "password": "secret123"},
        )
        user_id = r.json()["id"]

        show("① 不带令牌访问受保护接口 → 401")
        r = client.get("/auth/me")
        print("    状态码:", r.status_code, " 响应:", r.json())

        show("② 带一个乱写的令牌 → 401")
        r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        print("    状态码:", r.status_code, " 响应:", r.json())

        show("③ 正常登录后带令牌 → 200")
        r = client.post("/auth/login", json={"username": name, "password": "secret123"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get("/auth/me", headers=headers)
        print("    状态码:", r.status_code, " 响应:", r.json())

        show("④ 普通用户去分配角色 → 403")
        r = client.post(
            f"/users/{user_id}/roles",
            json={"role": "editor"},
            headers=headers,
        )
        print("    状态码:", r.status_code, " 响应:", r.json())
        print("    → 401 是没登录，403 是登录了但权限不够")

        show("⑤ 授予 admin 之后再试 → 200")
        grant_admin(user_id)
        r = client.post(
            f"/users/{user_id}/roles",
            json={"role": "editor"},
            headers=headers,
        )
        print("    状态码:", r.status_code, " 响应:", r.json())

        r = client.get(f"/users/{user_id}/roles")
        print("    查询角色:", r.json())

        show("⑥ 清理测试数据")
        with SessionLocal() as db:
            db.execute(delete(user_roles).where(user_roles.c.user_id == user_id))
            db.commit()
            u = db.get(User, user_id)
            if u is not None:
                db.delete(u)
                db.commit()
        print("    已清理")
