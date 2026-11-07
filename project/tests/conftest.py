"""pytest 公共配置。

两件事：
    1. 把仓库根目录加入 sys.path,测试里才能 import app；
    2. 提供 client 与 temp_user 两个 fixture。
"""

import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

warnings.filterwarnings("ignore")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture
def client():
    """不启动服务器,直接把请求打进应用。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def temp_user(client):
    """注册一个临时用户,测试结束后自动删除。"""
    stamp = int(time.time() * 1000) % 10**8
    username = f"t{stamp}"
    phone = f"1{stamp:010d}"
    password = "secret123"

    r = client.post(
        "/auth/register",
        json={"username": username, "phone": phone, "password": password},
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]

    yield {"id": user_id, "username": username, "password": password}

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is not None:
            db.delete(user)
            db.commit()
