# 第二章 · Python 数据库连接池

## 2.1 学习目标

本章讲解为什么要使用数据库连接池，以及如何用 `DBUtils.PooledDB` 实现，具体包括：

1. 理解一次数据库连接的建立过程及其代价
2. 理解连接池的工作原理：预建、借出、归还、上限控制
3. 掌握 `PooledDB` 的核心参数含义与取值依据
4. 能够用连接池改造原有的裸连接代码
5. 能够通过压测数据说明连接池带来的性能收益

前置知识：第一章（SQL 基础）、PyMySQL 基本用法。

> **本章的读法**：正文是教材写法，每个关键概念后面有一个「通俗理解」框。
> 本章两个案例都会自行关闭池子，不修改数据库中的数据。

---

## 2.2 为什么需要连接池

### 2.2.1 一次连接的建立过程

执行 `pymysql.connect()` 时，客户端与 MySQL 之间需要完成四个步骤：

| 步骤 | 内容 | 代价 |
| --- | --- | --- |
| ① TCP 三次握手 | 客户端连接服务器的 3306 端口 | 一个网络往返 |
| ② 服务端握手 | 服务器返回版本号、认证插件、随机盐值 | 一个网络往返 |
| ③ 身份认证 | 客户端提交凭据，MySQL 8 还需校验 RSA 公钥 | 计算 + 往返 |
| ④ 会话初始化 | 设置字符集、时区、`sql_mode`、`autocommit` 等 | 若干语句 |

四步完成后，才得到一个可以执行 SQL 的连接。而执行一条简单查询（如 `SELECT 1`）通常只需要不到 1 毫秒。

> **通俗理解**：打电话找人办事，先要拨号、等接通、报身份、寒暄几句，这些准备工作比真正要说的事还花时间。建连接就是这套"准备工作"。

### 2.2.2 不使用连接池的问题

若每次操作都新建连接、用完关闭，会产生三个问题：

| 问题 | 说明 |
| --- | --- |
| 建连开销重复支付 | 每次请求都要走完上述四步 |
| 并发上限受限 | MySQL 默认 `max_connections` 为 151，并发一高就报 `Too many connections` |
| 服务端资源抖动 | 连接频繁创建销毁，MySQL 需为每条连接分配线程和内存 |

### 2.2.3 连接池的基本思路

连接池的核心思想是"复用 + 限流"：

- **复用**：提前建好若干连接，重复使用，避免反复建连；
- **限流**：设定上限，超出上限的请求排队等待，保护数据库。

> **通俗理解**：出租车公司不会每来一个乘客就造一辆车，而是养一批车反复跑。车不够时让乘客排队，而不是无限制地造车把路堵死。

---

## 2.3 连接池的工作原理

### 2.3.1 池子的生命周期

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
          │ ② 空闲池空了，且总数 < maxconnections
          ▼
   ┌──────────────┐
   │ 新建一条连接  │
   └──────┬───────┘
          │ ③ 总数已达 maxconnections
          ▼
   blocking=True  → 排队等待
   blocking=False → 直接抛异常
```

三条规则：

| 规则 | 行为 |
| --- | --- |
| 借出时优先取空闲连接 | 有空闲就复用，没有才新建 |
| 归还时超过 `maxcached` | 多余连接真正关闭，避免闲置占用资源 |
| 总数达到 `maxconnections` | `blocking=True` 阻塞等待，`False` 抛 `PooledDBError` |

### 2.3.2 连接复用

连接池中的连接一旦建立就不会关闭，多次借还复用同一条物理连接。

示例文件：`chapters/ch02/code/01_pool_basic.py`

```python
conn = get_conn()          # 借
try:
    with conn.cursor() as cur:
        cur.execute("SELECT CONNECTION_ID()")
finally:
    conn.close()           # 还，不是断
```

运行结果：

```plain
--- ① 借一条连接，查一句 ---
    查询结果: (1,)

--- ② 连续借三次，看连接 id 是否复用 ---
    三次借到的连接 id: [519, 520, 519]
    去重后只有 2 个 —— 正好是池子预建的连接数，没有新建

--- ③ 池子的上限 ---
    maxconnections = 10
```

从结果可见：三次借还只用到 2 个连接 id，与 `mincached=2` 一致，说明连接被复用而非新建。

> **通俗理解**：`close()` 在池化语境下不是"断开"，而是"归还"。这三个字是本池化最重要的区别——忘记归还并不会立刻报错，但要借够 `maxconnections` 次之后，整个程序就会卡死。

### 2.3.3 池子上限与阻塞

`maxconnections` 是池子的并发上限，与数据库侧的 `max_connections` 是两个不同的概念。

部署多个进程时，数据库侧承受的连接总数为：

```plain
数据库侧连接数 = 进程数 × maxconnections
```

该值必须明显小于 MySQL 的 `max_connections`（默认 151），否则高峰期会出现 `Too many connections`。

> **通俗理解**：每个进程各有一个池子，互不共享。4 个 worker 各配 10，对数据库来说就是 40 条连接，不是 10 条。

---

## 2.4 PooledDB 的使用

### 2.4.1 安装

```bash
pip install DBUtils
```

导入时注意包名大小写：

```python
from dbutils.pooled_db import PooledDB     # 包名 DBUtils，导入名 dbutils
```

### 2.4.2 参数说明

```python
pool = PooledDB(
    creator=pymysql,              # 用哪个驱动创建连接
    mincached=2,                  # 启动时预建的连接数
    maxcached=5,                  # 空闲连接上限
    maxconnections=10,            # 池子上限
    blocking=True,                # 满了是等待还是报错
    ping=1,                       # 借出前探活
    **DB_CONFIG,
)
```

| 参数 | 作用 | 取值建议 |
| --- | --- | --- |
| `creator` | 创建连接使用的驱动 | `pymysql` |
| `mincached` | 初始化时预建的连接数 | 2 ~ 5 |
| `maxcached` | 空闲连接数上限，超出部分会被关闭 | 与 `maxconnections` 相当 |
| `maxconnections` | 池子允许的最大连接数 | 按并发峰值估算 |
| `blocking` | 达到上限时的行为 | Web 服务用 `True` |
| `ping` | 借出前是否探活 | 设为 `1` |

`ping=1` 的作用是解决 MySQL 的 `wait_timeout` 问题：MySQL 默认 8 小时无活动即断开连接，若池中连接已被服务端关闭而客户端不知情，下一次借出会拿到死连接并报 `Lost connection to MySQL server`。

> **通俗理解**：`ping=1` 就是每次借出前先问一句"你还在吗"。多花几毫秒，换掉一整类"半夜没人用，早上第一个请求就报错"的事故。

### 2.4.3 借还与关闭

```python
def get_conn():
    return pool.connection()      # 借

conn = get_conn()
try:
    ...
finally:
    conn.close()                  # 还

pool.close()                      # 进程退出前关闭整个池子
```

**注意**：借出的连接必须归还，否则池子会被逐步借空。归还应放在 `finally` 中，确保出现异常时也会执行。

### 2.4.4 完整定义

`chapters/ch02/code/pool.py` 中的实际定义：

```python
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "test_db"),
    "charset": "utf8mb4",
}

pool = PooledDB(
    creator=pymysql,
    mincached=2,
    maxcached=5,
    maxconnections=MAX_CONNECTIONS,
    blocking=True,
    ping=1,
    **DB_CONFIG,
)
```

池子在模块加载时创建一次，全进程共用。

---

## 2.5 性能对比实验

### 2.5.1 实验设计

对比两种方式的耗时：

| 方式 | 每次操作做什么 |
| --- | --- |
| 裸连接 | `pymysql.connect()` → 查询 → `close()` |
| 连接池 | `pool.connection()` → 查询 → `close()` |

实验条件：200 次查询，20 个线程并发。

### 2.5.2 运行结果

示例文件：`chapters/ch02/code/02_benchmark.py`

```plain
连接池上限 maxconnections=10

裸连接     200 次 / 20 线程    总耗时   2.280s    平均  11.40 ms/次
连接池     200 次 / 20 线程    总耗时   0.532s    平均   2.66 ms/次

连接池比裸连接快 4.3 倍
```

### 2.5.3 结果分析

单次查询耗时构成：

| 部分 | 耗时占比 |
| --- | --- |
| 建立连接（握手、认证、会话初始化） | 约 9 ms |
| 执行 `SELECT 1` | 不足 1 ms |

由此可见，裸连接的绝大部分时间消耗在建立连接上。若查询本身耗时较长（如 500 ms 的复杂报表），连接开销的占比会显著下降，此时优化 SQL 的收益大于引入连接池。

**注意**：连接池并非越大越好。上限低于并发数时，线程会排队等待；上限过大时，数据库侧的连接数会成为瓶颈。

> **通俗理解**：池子上限调到 2，20 个线程抢 2 条连接，大部分时间都在排队，反而更慢。合适的值要靠压测找，不能拍脑袋定。

---

## 2.6 常见错误

| 错误信息 | 原因 | 解决方法 |
| --- | --- | --- |
| `ModuleNotFoundError: dbutils` | 未安装 DBUtils | `pip install DBUtils` |
| `ModuleNotFoundError: pool` | 未在脚本所在目录执行 | 从仓库根目录用完整路径执行 |
| `Access denied for user 'root'` | 密码错误 | 检查 `MYSQL_PASSWORD` |
| 程序卡住且无报错 | 连接泄漏，池子被借空且 `blocking=True` | 检查每条借出是否都有 `close()` |
| `Lost connection to MySQL server` | 连接被 `wait_timeout` 断开 | 设置 `ping=1` |
| `Too many connections` | 进程数 × 池上限超过数据库限制 | 调小 `maxconnections` 或调大 `max_connections` |

---

## 2.7 本章小结

1. 建立连接需要 TCP 握手、认证、会话初始化四步，开销远大于执行简单查询。
2. 连接池的核心是复用与限流：预建连接重复使用，并设定上限保护数据库。
3. `close()` 在池化语境下表示归还而非断开；忘记归还会导致池子被借空并阻塞。
4. 关键参数为 `maxconnections`（上限）、`blocking`（满了怎么办）、`ping`（死连接怎么办）。
5. 实测 200 次查询、20 线程，裸连接 11.40 ms/次，池化后 2.66 ms/次，相差约 4.3 倍。
6. 池子大小需压测确定，过小会导致排队，过大会压垮数据库连接数。

---

## 2.8 练习

1. 将 `POOL_MIN_CACHED` 设为 4，重新运行案例 1，观察去重后的连接 id 个数变化。
2. 将 `POOL_MAX` 设为 2，重新运行案例 2，记录耗时并解释变化原因。
3. 对比 `chapters/ch02/code/legacy/demo-user-manager-sys.py`（裸连接）与 `chapters/ch02/code/user_dao.py`（池化），列出改造涉及的代码行。
4. 思考：如果数据库重启，池中所有连接都会失效，`ping=1` 能否完全替代重连逻辑？

---

<small>相关：[第一章 -- 环境搭建与连通](../../ch01/notes/阶段0%20--%20环境搭建与连通.md) · [第三章 -- SQLAlchemy ORM 基础](../../ch03/notes/SQLAlchemy%20ORM%20基础.md)</small>
