# 第二章 -- Python 数据库连接池

> 对应教程第二章。改造对象：`practice/legacy/demo-user-manager-sys.py`（裸连接版）
> 改造结果：`practice/ch02/`（池化版）

## 1. 学习目标

- 说清楚一次 MySQL 连接到底贵在哪
- 理解连接池的生命周期：预建 → 借出 → 归还 → 销毁
- 会用 `DBUtils.PooledDB`，并把每个参数对应到业务场景
- 把 legacy 版用户管理系统改成池化版，**接口签名不变**
- 用压测数据证明池化收益，并能解释收益从哪来
- 能回答连接池相关面试题

## 2. 基础概念：连接是什么

`pymysql.connect()` 不是"打开一个文件"，它背后至少做了四件事：

1. **TCP 三次握手** —— 客户端和 MySQL 的 3306 端口建立 socket
2. **服务端握手** —— 服务器发版本号、认证插件、salt
3. **身份认证** —— 客户端回 `caching_sha2_password` 凭据，MySQL 8 还要校验 RSA 公钥
4. **会话初始化** —— 设置字符集、时区、`sql_mode`、`autocommit` 等会话变量

只有这四步都走完，你才拿到一个能执行 SQL 的连接。这四步的网络往返加起来，通常比一句 `SELECT 1` 本身贵一到两个数量级。

## 3. 为什么需要连接池

### 3.1 裸连接的问题

legacy 版每次 `UserDB()` 都 `pymysql.connect()`，用完 `close()`。假设一个接口每秒处理 100 个请求，每个请求新建一次连接：

- 每秒 100 次握手 + 认证，CPU 和网络全耗在建连上
- MySQL 默认 `max_connections = 151`，并发一高直接报 `Too many connections`
- 连接频繁创建销毁，服务端要为每条连接分配线程和内存，抖动明显

### 3.2 连接池的思路

连接是**稀缺且可复用**的资源。既然建一次很贵，那就建好一批放在池子里，谁要用谁借，用完还回去，不销毁。

一句话概括：**用空间换时间，用上限换稳定。**

## 4. 原理：池子怎么运转

```plain
        启动时
          │
          ▼
   ┌──────────────┐   mincached=2，先建 2 条待命
   │  空闲连接池   │◄──────────────┐
   │  idle cache  │               │
   └──────┬───────┘               │
          │ ① connection() 借出    │ ④ close() 归还
          ▼                       │
   ┌──────────────┐               │
   │  使用中连接   │───────────────┘
   └──────┬───────┘
          │ ② 空闲池没有了，且总数 < maxconnections
          ▼
   ┌──────────────┐
   │ 新建一条连接  │
   └──────┬───────┘
          │ ③ 总数已达 maxconnections
          ▼
   blocking=True  → 排队等待
   blocking=False → 直接抛异常
```

三条关键规则：

| 规则 | 行为 |
| --- | --- |
| 借出时优先取空闲连接 | 有就复用，没有才新建 |
| 归还时超过 `maxcached` | 多出来的连接真关闭，避免闲置占资源 |
| 总数达到 `maxconnections` | `blocking=True` 阻塞等待，`False` 抛 `PooledDBError` |

## 5. 环境准备

```bash
pip install DBUtils
export MYSQL_PASSWORD=你的密码
```

本仓库已装 `DBUtils 3.2.0`，代码在 `practice/ch02/`。

> 注意：`DBUtils` 的包名是 `DBUtils`，导入时写 `from dbutils.pooled_db import PooledDB`，大小写不一致是正常的。

## 6. 完整代码

### 6.1 pool.py —— 池子只建一次

```python
pool = PooledDB(
    creator=pymysql,
    mincached=2,
    maxcached=5,
    maxconnections=10,
    blocking=True,
    ping=1,
    **DB_CONFIG,
)
```

要点：`pool` 是**模块级全局变量**，进程内只初始化一次。每个请求都 `PooledDB(...)` 一次，等于没有池。

### 6.2 user_dao.py —— 每借必还

```python
def get_user(self, uid: int) -> dict | None:
    conn = get_conn()          # 借
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute("SELECT id, username FROM user WHERE id = %s", (uid,))
            return cur.fetchone()
    finally:
        conn.close()           # 还
```

`try/finally` 不是可选项。中间抛异常而没 `close()`，这条连接就永久泄漏，借够 `maxconnections` 次之后整个池子卡死。

### 6.3 benchmark.py —— 用数据说话

```bash
python practice/ch02/benchmark.py
```

## 7. PooledDB 参数逐条解释

| 参数 | 含义 | 怎么定 |
| --- | --- | --- |
| `creator` | 用哪个驱动建连接 | `pymysql` |
| `mincached` | 初始化时预建的空闲连接数 | 服务启动后立刻有流量，设 2~5 |
| `maxcached` | 空闲连接上限，超出即关闭 | 一般等于或略小于 `maxconnections` |
| `maxconnections` | 池子上限 | 按并发峰值估，且必须小于 MySQL 的 `max_connections` |
| `maxshared` | 允许共享的连接数，0 表示全部独占 | 只读场景可共享，写事务必须是独占 |
| `blocking` | 池满时是等待还是报错 | Web 服务用 `True`，宁可排队也别 500 |
| `ping` | 借出前是否探活 | 设 `1`，解决 MySQL `wait_timeout` 断连 |
| `maxusage` | 单条连接最多复用多少次 | 默认 `None`（无限），怀疑连接状态污染时设个上限 |
| `setsession` | 建连后执行的会话初始化语句 | 如 `["SET SESSION sql_mode='STRICT_TRANS_TABLES'"]` |

**`ping=1` 为什么重要**：MySQL 默认 `wait_timeout = 28800`（8 小时）。凌晨没人访问，池里的连接全被服务端单方面断掉，第二天第一个请求拿到的是死连接，报 `Lost connection to MySQL server`。`ping=1` 在借出前先探一下，断了就自动重建。

## 8. 实战：legacy → 池化版

| 维度 | legacy 版 | 池化版 |
| --- | --- | --- |
| 连接来源 | `pymysql.connect()` 每次新建 | `pool.connection()` 借 |
| `close()` 语义 | 真断开 TCP | 归还池子 |
| 连接数 | 随并发线性增长 | 恒 ≤ `maxconnections` |
| 建连次数（200 次查询） | 200 次 | 10 次以内 |
| 代码改动量 | — | 只改连接获取方式，SQL 一行没动 |

这也说明一个设计原则：**连接管理属于基础设施，不该散落在业务代码里**。所以 `app/` 里对应的是 `db/engine.py`，SQLAlchemy 的连接池是 Engine 自带的，参数同样是这几个。

## 9. 实测结果

本机实测（200 次查询 / 20 线程）：

```plain
连接池上限 maxconnections=10

裸连接     200 次 / 20 线程    总耗时   2.366s    平均  11.83 ms/次
连接池     200 次 / 20 线程    总耗时   0.556s    平均   2.78 ms/次

连接池比裸连接快 4.3 倍
```

差距几乎全部来自建连开销：11.83 ms 里，真正执行 `SELECT 1` 的时间不到 0.5 ms。

## 10. 动手练习

1. 把 `POOL_MAX` 改成 `2`，`WORKERS` 改成 `20` 再跑压测，观察耗时变化，解释为什么变慢。
2. 把 `blocking` 改成 `False`，重复上一步，看看抛出的异常长什么样。
3. 故意删掉 `get_user` 里的 `finally: conn.close()`，写个 20 线程循环，观察多少次之后卡死。
4. 给 `UserDAO` 加一个 `transfer(from_id, to_id, amount)`，用池连接实现转账事务，验证异常时能回滚。

## 11. 常见错误排查

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| 卡住不动，无报错 | 连接泄漏，池被借空且 `blocking=True` | 检查每条借出是否都有 `close()` |
| `Too many connections` | `maxconnections` 总和超过 MySQL 上限 | 调小池上限，或调大 `max_connections` |
| `Lost connection to MySQL server` | 连接被 `wait_timeout` 断开 | `ping=1` |
| 数据莫名多出一条 | 归还前没 `commit`/`rollback`，事务状态带回池 | 统一在 `finally` 里处理事务收尾 |
| 多进程下池子失效 | 池是进程内对象，`fork` 后各自独立 | 每个进程各自建池，或用外部连接代理 |

## 12. 高频面试题

1. **什么是数据库连接池？为什么需要它？**
   预先创建并复用一组连接，避免每次请求都做 TCP 握手和认证，同时把并发连接数控制在数据库能承受的范围内。

2. **连接池的核心参数有哪些？怎么定？**
   `mincached`（预热）、`maxcached`（空闲上限）、`maxconnections`（并发上限）、`blocking`（满时策略）、`ping`（探活）。上限按"并发峰值 × 单请求连接持有时间"估算。

3. **连接池和线程是什么关系？**
   池本身要线程安全（`DBUtils` 内部用锁 + 条件变量实现），一条连接同一时刻只能被一个线程使用，除非显式开启 `maxshared` 共享模式。

4. **`close()` 之后连接真的断了吗？**
   池化版不是。`close()` 是把连接还回池子，物理连接仍然存在。这也是"忘记 close 会泄漏"这个说法在池化语境下的准确含义：泄漏的是**租约**，不是 TCP。

5. **SQLAlchemy 需要额外配连接池吗？**
   不需要，`create_engine` 自带 `QueuePool`，参数就是 `pool_size` / `max_overflow` / `pool_recycle` / `pool_pre_ping`，一一对应。所以 `app/db/engine.py` 里那几行就是本节的工程化版本。

## 13. 本章总结

- 连接贵在握手和认证，不在 SQL 执行
- 池化的本质是复用 + 限流：复用省时间，限流保稳定
- 三个必记参数：`maxconnections`（上限）、`blocking`（满了怎么办）、`ping`（死连接怎么办）
- 池化只改连接获取方式，业务 SQL 不该动。如果改动扩散到 DAO 以外，说明连接管理漏进了业务层
- 下一章进入 SQLAlchemy ORM，Engine 的 `pool_size` / `max_overflow` 就是本章概念的延续
