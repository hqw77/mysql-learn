"""第六章 · 案例 2：用 TestClient 调自己的 API（读接口）。

学到什么：
    不用起 uvicorn，TestClient 直接把请求打进 FastAPI 应用，
    这也是第七章写自动化测试的基础。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch06/code/02_api_read.py
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

warnings.filterwarnings("ignore")   # 屏蔽 TestClient 的依赖弃用提示，让输出干净

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    with TestClient(app) as client:
        show("① 健康检查")
        r = client.get("/health")
        print("    状态码:", r.status_code, " 响应:", r.json())

        show("② 用户列表（分页）")
        r = client.get("/users", params={"page": 1, "size": 2})
        body = r.json()
        print("    状态码:", r.status_code)
        print("    total =", body["total"], " page =", body["page"], " size =", body["size"])
        for item in body["items"]:
            print("   ", item)

        show("③ 用户详情")
        r = client.get("/users/1")
        print("    状态码:", r.status_code)
        print("    响应:", r.json())

        show("④ 查不存在的用户 → 404")
        r = client.get("/users/99999")
        print("    状态码:", r.status_code)
        print("    响应:", r.json())
        print("    ← 这行 JSON 来自 main.py 里的 AppError 处理器")

        show("⑤ 参数不合法 → 422（FastAPI 自动挡）")
        r = client.get("/users", params={"size": 999})
        print("    状态码:", r.status_code)
        print("    第一条错误:", r.json()["detail"][0]["msg"])

        show("⑥ 打开文档看看")
        r = client.get("/openapi.json")
        paths = sorted(r.json()["paths"].keys())
        print("    已注册的接口:", paths)
