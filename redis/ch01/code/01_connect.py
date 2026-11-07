"""Redis 第一章 · 案例 1：连接与连接池。

学到什么：
    1. 单连接与连接池的区别
    2. decode_responses 的作用
    3. 怎么看服务端版本、当前 key 数量

怎么跑：
    python redis/ch01/code/01_connect.py

前提：Redis 已在 127.0.0.1:6379 运行。
"""

import redis

HOST = "127.0.0.1"
PORT = 6379


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    show("① 单连接：每次 new 一个,用完即弃")
    r = redis.Redis(host=HOST, port=PORT, db=0, decode_responses=True)
    print("    PING:", r.ping())
    r.close()

    show("② 连接池：全进程一份,反复复用")
    pool = redis.ConnectionPool(
        host=HOST,
        port=PORT,
        db=0,
        decode_responses=True,
        max_connections=20,
    )
    client = redis.Redis(connection_pool=pool)
    print("    PING:", client.ping())
    print("    池子最大连接数:", pool.max_connections)

    show("③ 服务端信息")
    info = client.info()
    print("    Redis 版本:", info["redis_version"])
    print("    运行模式  :", info["redis_mode"])
    print("    已用内存  :", f"{info['used_memory_human']}")

    show("④ decode_responses 的影响")
    raw_client = redis.Redis(host=HOST, port=PORT, db=0)          # 默认 False
    raw_client.set("demo:decode", "中文值")
    print("    decode=False ->", raw_client.get("demo:decode"), " (bytes)")
    print("    decode=True  ->", client.get("demo:decode"), " (str)")
    raw_client.delete("demo:decode")
    raw_client.close()

    show("⑤ 当前库里有几个 key")
    print("    DBSIZE:", client.dbsize())

    client.close()
    print("\n完成。单连接用完要 close,池子由进程统一管理。")
