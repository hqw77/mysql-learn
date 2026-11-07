"""Redis 第一章 · 案例 4：过期时间与 key 管理。

学到什么：
    TTL 是缓存的生命线；SCAN 替代 KEYS；命名规范让 key 可维护。

怎么跑：
    python redis/ch01/code/04_expire_and_key.py
"""

import time

import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
PREFIX = "demo:ttl:"


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    for k in r.scan_iter(f"{PREFIX}*"):
        r.delete(k)

    show("① EXPIRE：给已有 key 设置过期")
    r.set(f"{PREFIX}session", "abc123")
    print("    刚设置时 TTL:", r.ttl(f"{PREFIX}session"), " → -1 表示永不过期")
    r.expire(f"{PREFIX}session", 30)
    print("    EXPIRE 30 后 TTL:", r.ttl(f"{PREFIX}session"), "秒")

    show("② SET 时直接带过期（推荐）")
    r.set(f"{PREFIX}code", "8888", ex=60)
    print("    TTL:", r.ttl(f"{PREFIX}code"), "秒")
    r.set(f"{PREFIX}code2", "9999", px=5000)
    print("    毫秒级 PX 5000 → TTL:", r.ttl(f"{PREFIX}code2"), "秒")

    show("③ TTL 的三种返回值")
    print("    key 不存在:", r.ttl(f"{PREFIX}nothing"), " → -2")
    print("    key 无过期:", end=" ")
    r.set(f"{PREFIX}forever", "x")
    print(r.ttl(f"{PREFIX}forever"), " → -1")
    print("    有过期     :", r.ttl(f"{PREFIX}code"), " → 剩余秒数")

    show("④ PERSIST：去掉过期,变永久")
    r.persist(f"{PREFIX}code")
    print("    PERSIST 后 TTL:", r.ttl(f"{PREFIX}code"), " → -1")

    show("⑤ 过期是被动的：到点不会立刻消失")
    r.set(f"{PREFIX}short", "v", px=300)
    print("    设置 300ms 后:", r.get(f"{PREFIX}short"))
    time.sleep(0.5)
    print("    等 0.5 秒后 :", r.get(f"{PREFIX}short"), " → 已过期")
    print("    TTL:", r.ttl(f"{PREFIX}short"), " → -2（key 不存在）")
    print("    → Redis 用惰性删除 + 定期抽样清理,内存不会立刻释放")

    show("⑥ SCAN：遍历 key 的正确方式")
    for i in range(5):
        r.set(f"{PREFIX}item:{i}", i)
    keys = sorted(r.scan_iter(f"{PREFIX}item:*"))
    print("    SCAN 匹配到:", keys)
    print("    ❌ 不要用 KEYS：它会一次性扫描全部 key,生产环境会阻塞服务")

    show("⑦ 删除：DEL 与 UNLINK")
    print("    DEL 同步删除:", r.delete(f"{PREFIX}item:0"))
    print("    UNLINK 异步删除（大 key 用）:", r.unlink(f"{PREFIX}item:1"))

    show("⑧ 命名规范")
    print("    推荐: 业务:对象:标识     例 user:42   order:2024:88")
    print("    带环境: prod:user:42     dev:user:42")
    print("    禁止: 都用 user_42 这种没有分层的前缀,量大后无法批量管理")

    show("⑨ 清理")
    for k in r.scan_iter(f"{PREFIX}*"):
        r.delete(k)
    print("    已清理")
