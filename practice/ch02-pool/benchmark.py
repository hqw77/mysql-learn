"""压测对比：每次新建连接 vs 从连接池借。

运行：
    export MYSQL_PASSWORD=你的密码
    python practice/ch02-pool/benchmark.py

看两件事：
    1. 耗时差距 —— 建连接要 TCP 握手 + 认证，比执行 SELECT 1 贵得多
    2. 连接数   —— 裸连版本会把 max_connections 打满，池化版恒定在上限之内
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pymysql

from pool import DB_CONFIG, MAX_CONNECTIONS, close_pool, get_conn

TASKS = 200      # 总共查多少次
WORKERS = 20     # 同时多少个线程


def query_once_raw():
    """裸连接：connect -> 查 -> close，每次都是一条新的 TCP 连接。"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    finally:
        conn.close()          # 真正断开


def query_once_pool():
    """连接池：借 -> 查 -> 还，物理连接始终复用。"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    finally:
        conn.close()          # 归还，不断开


def run(label: str, func) -> float:
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        list(executor.map(lambda _: func(), range(TASKS)))
    cost = time.perf_counter() - start
    print(
        f"{label:<6} {TASKS:>4} 次 / {WORKERS} 线程    "
        f"总耗时 {cost:7.3f}s    平均 {cost / TASKS * 1000:6.2f} ms/次"
    )
    return cost


if __name__ == "__main__":
    print(f"连接池上限 maxconnections={MAX_CONNECTIONS}\n")

    raw = run("裸连接", query_once_raw)
    pooled = run("连接池", query_once_pool)

    print(f"\n连接池比裸连接快 {raw / pooled:.1f} 倍")
    print("注意：差距主要来自建连接的开销，数据量越大差距越明显")

    close_pool()
