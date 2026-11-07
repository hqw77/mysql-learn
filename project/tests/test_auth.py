"""第七章 · 认证接口的自动化测试。

运行：
    python -m pytest tests -v
"""

from app.db.session import SessionLocal
from app.models import User


def test_register_success(client):
    """注册成功返回 201,且响应里不含密码字段。"""
    import time

    stamp = int(time.time() * 1000) % 10**8
    r = client.post(
        "/auth/register",
        json={"username": f"t{stamp}", "phone": f"1{stamp:010d}", "password": "secret123"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == f"t{stamp}"
    assert "password" not in body
    assert "password_hash" not in body

    # 清理
    with SessionLocal() as db:
        user = db.get(User, body["id"])
        if user is not None:
            db.delete(user)
            db.commit()


def test_register_duplicate(client, temp_user):
    """重复注册返回 409。"""
    r = client.post(
        "/auth/register",
        json={
            "username": temp_user["username"],
            "phone": "19999999999",
            "password": "secret123",
        },
    )
    assert r.status_code == 409


def test_register_weak_password(client):
    """密码过短由 schema 拦下,返回 422。"""
    import time

    stamp = int(time.time() * 1000) % 10**8
    r = client.post(
        "/auth/register",
        json={"username": f"w{stamp}", "phone": f"1{stamp:010d}", "password": "123"},
    )
    assert r.status_code == 422


def test_login_success(client, temp_user):
    """登录成功返回令牌。"""
    r = client.post(
        "/auth/login",
        json={"username": temp_user["username"], "password": temp_user["password"]},
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert len(r.json()["access_token"]) > 20


def test_login_wrong_password(client, temp_user):
    """密码错误返回 401。"""
    r = client.post(
        "/auth/login",
        json={"username": temp_user["username"], "password": "wrong-password"},
    )
    assert r.status_code == 401


def test_me_without_token(client):
    """不带令牌访问受保护接口,返回 401。"""
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_with_token(client, temp_user):
    """带令牌访问,返回当前用户信息。"""
    login = client.post(
        "/auth/login",
        json={"username": temp_user["username"], "password": temp_user["password"]},
    )
    token = login.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == temp_user["username"]


def test_assign_role_forbidden(client, temp_user):
    """普通用户分配角色,返回 403。"""
    login = client.post(
        "/auth/login",
        json={"username": temp_user["username"], "password": temp_user["password"]},
    )
    token = login.json()["access_token"]

    r = client.post(
        f"/users/{temp_user['id']}/roles",
        json={"role": "editor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
