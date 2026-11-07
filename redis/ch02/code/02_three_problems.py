"""Redis 第二章 · 案例 2：缓存穿透、击穿、雪崩的复现与防护。

学到什么：
    穿透 = 查不存在的数据,每次都打到库
    击穿 = 热点 key 过期瞬间,并发全部打到库
    雪崩 = 大批 key 同时过期,库被瞬间打垮

怎么跑：
    python redis/ch02/code/02_three_problems.py
"""

import json
import random
import threading
import time

import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
PREFIX = "demo:problem:"


class FakeDB:
    def __init__(self) -> None:
        self.rows = {1: {"id": 1, "username": "张三"}}
        self.hits = 0
        self._lock = threading.Lock()

    def get_user(self, user_id: int):
        with self._lock:
            self.hits += 1
        time.sleep(0.05)
        return self.rows.get(user_id)


db = FakeDB()


def show(title: str) -> None:
    print(f"\n--- {title} ---")


def clean() -> None:
    for k in r.scan_iter(f"{PREFIX}*"):
        r.delete(k)


# ---------------------------------------------------------------- 穿透
def read_plain(user_id: int):
    """不做任何防护：查不到就查不到,下次还查。"""
    key = f"{PREFIX}plain:{user_id}"
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached)
    user = db.get_user(user_id)
    if user is not None:
        r.set(key, json.dumps(user, ensure_ascii=False), ex=60)
    return user


def read_with_null_cache(user_id: int):
    """防护：把"不存在"也缓存起来（短 TTL）。"""
    key = f"{PREFIX}null:{user_id}"
    cached = r.get(key)
    if cached is not None:
        return None if cached == "__NULL__" else json.loads(cached)

    user = db.get_user(user_id)
    if user is None:
        r.set(key, "__NULL__", ex=30)      # 空值缓存,TTL 短一些
        return None

    r.set(key, json.dumps(user, ensure_ascii=False), ex=300)
    return user


# ---------------------------------------------------------------- 击穿
def read_no_lock(user_id: int):
    """热点 key 过期后,并发请求全部穿透到数据库。"""
    key = f"{PREFIX}hot"
    cached = r.get(key)
    if cached is not None:
        return cached
    time.sleep(0.05)                       # 模拟查库
    value = json.dumps(db.get_user(user_id), ensure_ascii=False)
    r.set(key, value, ex=300)
    return value


def read_with_lock(user_id: int):
    """防护：只让一个请求去查库,其他等待。"""
    key = f"{PREFIX}hot"
    cached = r.get(key)
    if cached is not None:
        return cached

    lock_key = f"{PREFIX}hot:lock"
    got = r.set(lock_key, "1", nx=True, ex=5)
    if got:
        try:
            time.sleep(0.05)               # 模拟查库
            value = json.dumps(db.get_user(user_id), ensure_ascii=False)
            r.set(key, value, ex=300)
            return value
        finally:
            r.delete(lock_key)

    # 没抢到锁：等一会儿再读缓存
    time.sleep(0.1)
    return r.get(key)


# ---------------------------------------------------------------- 雪崩
def set_many_uniform(n: int = 20) -> None:
    """所有 key 用同一个 TTL → 同生共死。"""
    pipe = r.pipeline()
    for i in range(n):
        pipe.set(f"{PREFIX}avalanche:{i}", i, ex=60)
    pipe.execute()


def set_many_jitter(n: int = 20) -> None:
    """TTL 加随机抖动 → 过期时间打散。"""
    pipe = r.pipeline()
    for i in range(n):
        ttl = 60 + random.randint(0, 30)   # 60~90 秒
        pipe.set(f"{PREFIX}jitter:{i}", i, ex=ttl)
    pipe.execute()


if __name__ == "__main__":
    clean()

    show("① 穿透：查询一个不存在的 id,100 次")
    before = db.hits
    for _ in range(100):
        read_plain(999999)
    print(f"    数据库被查了 {db.hits - before} 次  ← 缓存毫无作用")

    show("② 防护后：把空值也缓存")
    before = db.hits
    for _ in range(100):
        read_with_null_cache(999999)
    print(f"    数据库被查了 {db.hits - before} 次  ← 只有第一次")

    show("③ 击穿：热点 key 不存在,10 个线程同时来")
    r.delete(f"{PREFIX}hot")
    before = db.hits
    threads = [threading.Thread(target=read_no_lock, args=(1,)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"    数据库被查了 {db.hits - before} 次  ← 全部穿透")

    show("④ 防护后：加互斥锁,只放一个进去")
    r.delete(f"{PREFIX}hot")
    before = db.hits
    threads = [threading.Thread(target=read_with_lock, args=(1,)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"    数据库被查了 {db.hits - before} 次  ← 只有拿到锁的那个")

    show("⑤ 雪崩：20 个 key 用同一个 TTL")
    set_many_uniform()
    ttls = [r.ttl(f"{PREFIX}avalanche:{i}") for i in range(5)]
    print("    前 5 个 key 的 TTL:", ttls, " ← 完全一样,会同一秒集体过期")

    show("⑥ 防护后：TTL 加随机抖动")
    set_many_jitter()
    ttls = [r.ttl(f"{PREFIX}jitter:{i}") for i in range(5)]
    print("    前 5 个 key 的 TTL:", ttls, " ← 被打散了")

    show("⑦ 三种问题对照")
    rows = [
        ("穿透", "查不存在的数据", "空值缓存 / 布隆过滤器 / 参数校验"),
        ("击穿", "单个热点 key 过期", "互斥锁 / 逻辑过期 / 预热"),
        ("雪崩", "大批 key 同时过期", "TTL 抖动 / 多级缓存 / 熔断降级"),
    ]
    for name, cause, fix in rows:
        print(f"    {name}  {cause:16} {fix}")

    show("⑧ 清理")
    clean()
    print("    已清理")
