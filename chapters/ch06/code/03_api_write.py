"""第六章 · 案例 3：写接口 —— 创建 / 改余额 / 删除。

学到什么：
    状态码不是随便定的：创建 201、冲突 409、删除 204、查不到 404。
    业务异常在 service 抛,main 里的处理器统一转成 HTTP 响应。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch06/code/03_api_write.py
"""

import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

warnings.filterwarnings("ignore")   # 屏蔽 TestClient 的依赖弃用提示,让输出干净

from decimal import Decimal  # noqa: E402,F401

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

STAMP = int(time.time()) % 100000


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    username = f"api{STAMP}"
    phone = f"137{STAMP:08d}"

    with TestClient(app) as client:
        show("① 创建用户 → 201")
        r = client.post("/users", json={"username": username, "phone": phone, "balance": "100.00"})
        print("    状态码:", r.status_code)
        body = r.json()
        print("    响应:", body)
        user_id = body["id"]

        show("② 再建一个同名的 → 409")
        r = client.post("/users", json={"username": username, "phone": f"136{STAMP:08d}"})
        print("    状态码:", r.status_code)
        print("    响应:", r.json())
        print("    ← service 抛 ConflictError,main 转成 409")

        show("③ 入参不合法 → 422（还没进 service）")
        r = client.post("/users", json={"username": "x", "phone": "123"})
        print("    状态码:", r.status_code)
        for e in r.json()["detail"]:
            print(f"    {e['loc'][-1]}: {e['msg']}")

        show("④ 调整余额 → 200")
        r = client.put(f"/users/{user_id}/balance", json={"amount": "50.00"})
        print("    状态码:", r.status_code, " 新余额:", r.json()["balance"])

        show("⑤ 删除（软删）→ 204")
        r = client.delete(f"/users/{user_id}")
        print("    状态码:", r.status_code, " 响应体:", repr(r.text))

        show("⑥ 删除后：列表里消失了,但详情还在")
        r = client.get("/users", params={"size": 100})
        names = [i["username"] for i in r.json()["items"]]
        print(f"    列表里有它吗: {username in names}   ← list 过滤了 is_deleted")
        r = client.get(f"/users/{user_id}")
        print("    详情状态码:", r.status_code, " is_deleted =", r.json()["is_deleted"])
        print("    ⚠️ 详情不过滤软删,这是产品决策,不是 bug")

        show("⑦ 清理：真删掉这条测试数据")
        with SessionLocal() as db:
            u = db.get(User, user_id)
            if u is not None:
                db.delete(u)
                db.commit()
        print("    已清理")

    show("状态码速记")
    print("    200 查到/改成功   201 创建成功   204 删除成功（无响应体）")
    print("    400 业务参数错    404 查不到      409 冲突（唯一键）")
    print("    422 格式校验失败（FastAPI 自动）  500 没捕获的异常")
