"""Redis 第二章 · 案例 3：先删缓存还是先改库？

学到什么：
    路径 A（先删缓存）会在并发下留下永久脏数据；
    路径 B（先改库、后删缓存）最多出现一次短暂旧值,随后自愈。

怎么跑：
    python redis/ch02/code/03_consistency.py

用分步模拟代替真实并发,把每一步的状态打印出来。
"""

import json

import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)
KEY = "demo:consistent:user:1"


def show(title: str) -> None:
    print(f"\n--- {title} ---")


def state(tag: str, db_value: str, cache_value) -> None:
    print(f"    {tag:12} 数据库={db_value:6} 缓存={cache_value}")


def reset(value: str = "888.00") -> None:
    r.set(KEY, json.dumps({"id": 1, "balance": value}, ensure_ascii=False), ex=300)


if __name__ == "__main__":
    # ============================================================ 路径 A
    show("① 路径 A：先删缓存,再改数据库（有问题的写法）")
    reset("888.00")
    state("初始", "888.00", r.get(KEY))

    print("    写线程：删除缓存")
    r.delete(KEY)
    state("删缓存后", "888.00", r.get(KEY))

    print("    读线程：缓存没了 → 查库拿到旧值 888 → 回写缓存")
    old = json.loads(json.dumps({"id": 1, "balance": "888.00"}))
    r.set(KEY, json.dumps(old, ensure_ascii=False), ex=300)
    state("读回写后", "888.00", r.get(KEY))

    print("    写线程：现在才更新数据库为 588")
    state("改库后", "588.00", r.get(KEY))
    print("    ⚠️ 缓存里是 888,数据库是 588,而且这个脏值会一直留到 TTL 过期")

    # ============================================================ 路径 B
    show("② 路径 B：先改数据库,再删缓存（推荐写法）")
    reset("888.00")
    state("初始", "888.00", r.get(KEY))

    print("    写线程：先更新数据库为 588")
    state("改库后", "588.00", r.get(KEY))

    print("    写线程：再删除缓存")
    r.delete(KEY)
    state("删缓存后", "588.00", r.get(KEY))

    print("    读线程：未命中 → 查库拿到 588 → 回写")
    r.set(KEY, json.dumps({"id": 1, "balance": "588.00"}, ensure_ascii=False), ex=300)
    state("读回写后", "588.00", r.get(KEY))
    print("    ✅ 最坏情况只是有一个读者短暂读到旧值,之后自愈")

    show("③ 为什么是「删缓存」而不是「更新缓存」")
    print("    更新缓存：要处理「两个写者先后更新」的顺序问题,可能写进旧值")
    print("    删除缓存：下次读自然重建,逻辑简单,出错概率低")
    print("    → 业界标准做法：改库 + 删缓存（Cache-Aside）")

    show("④ 极端情况：删缓存失败怎么办")
    print("    方案一：延迟双删（改库后 delete,sleep 500ms 再 delete 一次）")
    print("    方案二：把删除操作放进消息队列,失败自动重试")
    print("    方案三：给缓存设较短 TTL 兜底（最终一致）")

    show("⑤ 清理")
    r.delete(KEY)
    print("    已清理")
