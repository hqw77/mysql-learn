"""Redis 第二章 · 案例 1：Cache-Aside 的完整读写路径。

学到什么：
    1. 读:先查缓存,未命中再查库,回写缓存
    2. 写:先改库,再删缓存
    3. 用"查询次数"和"耗时"证明缓存有效

怎么跑：
    python redis/ch02/code/01_cache_aside.py

不依赖 MySQL,用一个带 50ms 延迟的假数据库模拟慢查询。
"""

import json
import time

import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
PREFIX = "demo:aside:"
TTL = 300


class FakeDB:
    """模拟 MySQL：每次都慢 50ms,并记录被查询的次数。"""

    def __init__(self) -> None:
        self.rows = {
            1: {"id": 1, "username": "张三", "balance": "888.00"},
            2: {"id": 2, "username": "李四", "balance": "400.00"},
        }
        self.query_count = 0

    def get_user(self, user_id: int):
        self.query_count += 1
        time.sleep(0.05)                 # 模拟数据库往返
        return self.rows.get(user_id)

    def update_balance(self, user_id: int, balance: str) -> None:
        self.query_count += 1
        time.sleep(0.05)
        self.rows[user_id]["balance"] = balance


db = FakeDB()


def show(title: str) -> None:
    print(f"\n--- {title} ---")


def get_user_cached(user_id: int):
    """Cache-Aside 读路径。"""
    key = f"{PREFIX}user:{user_id}"

    # ① 先查缓存
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached)

    # ② 未命中,查数据库
    print(f"    [未命中]    {key} → 查数据库")
    user = db.get_user(user_id)
    if user is None:
        return None

    # ③ 回写缓存
    r.set(key, json.dumps(user, ensure_ascii=False), ex=TTL)
    return user


def update_user_balance(user_id: int, balance: str) -> None:
    """Cache-Aside 写路径：先改库,再删缓存。"""
    db.update_balance(user_id, balance)
    r.delete(f"{PREFIX}user:{user_id}")
    print(f"    [写] 改库完成,已删除缓存 {PREFIX}user:{user_id}")


if __name__ == "__main__":
    for k in r.scan_iter(f"{PREFIX}*"):
        r.delete(k)

    show("① 第一次读：缓存为空,穿透到数据库")
    before = db.query_count
    print("    结果:", get_user_cached(1))
    print(f"    数据库查询次数: {db.query_count - before}")

    show("② 第二次读：直接命中缓存")
    before = db.query_count
    print("    结果:", get_user_cached(1))
    print(f"    数据库查询次数: {db.query_count - before}  ← 没有增长")

    show("③ 连续读 100 次：只有第一次查库")
    before = db.query_count
    start = time.perf_counter()
    for _ in range(100):
        get_user_cached(1)
    cost = (time.perf_counter() - start) * 1000
    print(f"    数据库查询次数: {db.query_count - before}")
    print(f"    100 次总耗时: {cost:.1f} ms  平均 {cost / 100:.2f} ms/次")

    show("④ 写操作：改库 + 删缓存")
    update_user_balance(1, "588.00")
    print("    缓存还在吗:", r.exists(f"{PREFIX}user:1"))

    show("⑤ 写后再读：会重新加载到最新值")
    before = db.query_count
    print("    结果:", get_user_cached(1))
    print(f"    数据库查询次数: {db.query_count - before}  ← 重建了一次")

    show("⑥ 对比：不走缓存要多久")
    start = time.perf_counter()
    for _ in range(100):
        db.get_user(1)
    cost = (time.perf_counter() - start) * 1000
    print(f"    100 次总耗时: {cost:.1f} ms  平均 {cost / 100:.2f} ms/次")

    show("⑦ 清理")
    for k in r.scan_iter(f"{PREFIX}*"):
        r.delete(k)
    print("    已清理")
