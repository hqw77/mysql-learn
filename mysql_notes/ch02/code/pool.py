"""连接池：进程内全局只建一次,所有 DAO 共用。

对比 mysql_notes/ch02/code/legacy/demo-user-manager-sys.py：
    那边每个 UserDB 实例都 pymysql.connect() 一次,close() 是真断 TCP；
    这边 pymysql.connect() 只在池子初始化时按 mincached 预建,
    之后的 connection() 是"借",close() 是"还",连接一直活着。
"""

import os

import pymysql
from dbutils.pooled_db import PooledDB

# 连接参数：密码一律从环境变量读,不写进代码
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "test_db"),
    "charset": "utf8mb4",
}

# 池子上限,压测脚本里也要用,单独提出来
MAX_CONNECTIONS = int(os.getenv("POOL_MAX", 10))

pool = PooledDB(
    creator=pymysql,                                  # 底层用什么驱动建连接
    mincached=int(os.getenv("POOL_MIN_CACHED", 2)),   # 启动时先建几条待命
    maxcached=int(os.getenv("POOL_MAX_CACHED", 5)),   # 空闲连接最多留几条,多的关掉
    maxconnections=MAX_CONNECTIONS,                   # 池子上限,超过就排队
    blocking=True,                                    # 池满时等待；False 则直接抛异常
    ping=1,                                           # 每次借出前 ping 一次,坏连接自动重建
    **DB_CONFIG,
)


def get_conn():
    """借一条连接。用完必须 conn.close() 归还,否则池子会被借空。"""
    return pool.connection()


def close_pool() -> None:
    """进程退出前调用,关闭池中所有空闲连接。"""
    pool.close()
