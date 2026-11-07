"""Redis 第一章 · 案例 3：List、Set、ZSet。

学到什么：
    List 当队列/栈；Set 做去重与集合运算；ZSet 做排行榜。

怎么跑：
    python redis/ch01/code/03_list_set_zset.py
"""

import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
PREFIX = "demo:lss:"


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    show("① List：左边进右边出 = 队列（FIFO）")
    r.delete(f"{PREFIX}queue")
    for task in ("task-1", "task-2", "task-3"):
        r.rpush(f"{PREFIX}queue", task)          # 右边进
    print("    队列内容:", r.lrange(f"{PREFIX}queue", 0, -1))
    print("    取出一个:", r.lpop(f"{PREFIX}queue"))   # 左边出
    print("    剩余:", r.lrange(f"{PREFIX}queue", 0, -1))

    show("② List：同一边进出一边出 = 栈（LIFO）")
    r.delete(f"{PREFIX}stack")
    for page in ("page-1", "page-2", "page-3"):
        r.rpush(f"{PREFIX}stack", page)
    print("    压栈顺序:", r.lrange(f"{PREFIX}stack", 0, -1))
    print("    弹出一个:", r.rpop(f"{PREFIX}stack"))     # 右边出
    print("    剩余:", r.lrange(f"{PREFIX}stack", 0, -1))

    show("③ List：只保留最近 N 条（消息流）")
    r.delete(f"{PREFIX}logs")
    for i in range(10):
        r.lpush(f"{PREFIX}logs", f"log-{i}")
        r.ltrim(f"{PREFIX}logs", 0, 4)                 # 只留 5 条
    print("    最新 5 条:", r.lrange(f"{PREFIX}logs", 0, -1))
    print("    总长度:", r.llen(f"{PREFIX}logs"))

    show("④ Set：去重 + 集合运算")
    r.delete(f"{PREFIX}tag:a", f"{PREFIX}tag:b")
    r.sadd(f"{PREFIX}tag:a", "python", "mysql", "redis")
    r.sadd(f"{PREFIX}tag:b", "python", "redis", "docker")
    print("    A 的标签:", sorted(r.smembers(f"{PREFIX}tag:a")))
    print("    B 的标签:", sorted(r.smembers(f"{PREFIX}tag:b")))
    print("    交集（共同标签）:", sorted(r.sinter(f"{PREFIX}tag:a", f"{PREFIX}tag:b")))
    print("    并集:", sorted(r.sunion(f"{PREFIX}tag:a", f"{PREFIX}tag:b")))
    print("    差集 A-B:", sorted(r.sdiff(f"{PREFIX}tag:a", f"{PREFIX}tag:b")))
    print("    python 在 A 里吗:", r.sismember(f"{PREFIX}tag:a", "python"))

    show("⑤ ZSet：按分数排序 = 排行榜")
    key = f"{PREFIX}rank"
    r.delete(key)
    r.zadd(key, {"张三": 888, "李四": 400, "王五": 100})
    print("    正序（分数低的在前）:", r.zrange(key, 0, -1, withscores=True))
    print("    倒序（榜单前三）:", r.zrevrange(key, 0, 2, withscores=True))
    print("    李四的排名（从 0 开始）:", r.zrank(key, "李四"))
    print("    张三的分数:", r.zscore(key, "张三"))
    r.zincrby(key, 50, "王五")
    print("    王五加 50 分后倒序:", r.zrevrange(key, 0, -1, withscores=True))
    print("    分数区间 [100,500] 内:", r.zrangebyscore(key, 100, 500))

    show("⑥ 五种类型对照")
    rows = [
        ("String", "单值、计数、锁", "set/get/incr/setnx"),
        ("Hash", "对象的多个字段", "hset/hget/hincrby"),
        ("List", "队列、栈、最近 N 条", "lpush/rpop/ltrim"),
        ("Set", "去重、标签、交集", "sadd/sinter/sismember"),
        ("ZSet", "排行榜、延时队列", "zadd/zrevrange/zrank"),
    ]
    for name, use, cmd in rows:
        print(f"    {name:8} {use:22} {cmd}")

    show("⑦ 清理")
    for k in r.scan_iter(f"{PREFIX}*"):
        r.delete(k)
    print("    已清理")
