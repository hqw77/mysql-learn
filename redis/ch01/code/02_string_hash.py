"""Redis 第一章 · 案例 2：String 与 Hash。

学到什么：
    String 适合存单值、计数器；Hash 适合存对象的多个字段。

怎么跑：
    python redis/ch01/code/02_string_hash.py
"""

import time

import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
PREFIX = "demo:string_hash:"


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    r.delete(
        f"{PREFIX}name", f"{PREFIX}visits", f"{PREFIX}user:1",
        f"{PREFIX}counter", f"{PREFIX}lock",
    )

    show("① String 基本读写")
    r.set(f"{PREFIX}name", "张三")
    print("    GET:", r.get(f"{PREFIX}name"))
    print("    不存在的 key:", r.get(f"{PREFIX}nobody"))

    show("② 计数器:INCR 是原子操作")
    r.set(f"{PREFIX}visits", 100)
    print("    初始:", r.get(f"{PREFIX}visits"))
    print("    INCR:", r.incr(f"{PREFIX}visits"))
    print("    INCRBY 10:", r.incrby(f"{PREFIX}visits", 10))
    print("    DECRBY 5 :", r.decrby(f"{PREFIX}visits", 5))
    print("    → 全程不需要先读再写,不会丢更新")

    show("③ 批量读写")
    r.mset({f"{PREFIX}a": "1", f"{PREFIX}b": "2"})
    print("    MGET:", r.mget(f"{PREFIX}a", f"{PREFIX}b", f"{PREFIX}nobody"))

    show("④ SET NX / XX：只有不存在才写（分布式锁的雏形）")
    ok1 = r.set(f"{PREFIX}lock", "owner-A", nx=True, ex=10)
    ok2 = r.set(f"{PREFIX}lock", "owner-B", nx=True, ex=10)
    print("    第一次（key 不存在）:", ok1)
    print("    第二次（key 已存在）:", ok2, " → 抢锁失败")
    print("    剩余 TTL:", r.ttl(f"{PREFIX}lock"), "秒")
    print("    锁的持有者:", r.get(f"{PREFIX}lock"))

    show("⑤ Hash：存一个对象的多个字段")
    key = f"{PREFIX}user:1"
    r.hset(key, mapping={
        "username": "张三",
        "phone": "13800000001",
        "balance": "888.00",     # 金额用字符串存,不要用 HINCRBY
        "points": "0",           # 整数才能 HINCRBY
    })
    print("    HGETALL:", r.hgetall(key))
    print("    HGET balance:", r.hget(key, "balance"))
    print("    HINCRBY points 12:", r.hincrby(key, "points", 12))
    print("    字段数:", r.hlen(key))
    print("    所有字段名:", r.hkeys(key))
    print("    ⚠️ HINCRBY balance 会报错 'hash value is not an integer'")
    print("       → 金额是小数,Redis 的 INCR 系列只支持整数；金额请用 String + 应用层算")

    show("⑥ String 与 Hash 的选择")
    print("    存单个值（计数、开关、令牌）→ String")
    print("    存对象且只改部分字段      → Hash（改一个字段不用整体覆盖）")
    print("    需要 TTL 的整个对象       → 还是 String + JSON（Hash 只能给 key 设过期）")

    time.sleep(0.1)
    show("⑦ 清理")
    for k in r.scan_iter(f"{PREFIX}*"):
        r.delete(k)
    print("    已清理")
