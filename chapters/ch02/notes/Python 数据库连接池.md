# 第二章 · Python 数据库连接池

> **一句话**：连接是稀缺资源，建一次很贵——所以建好一批放着，谁用谁借，用完还回去。

**学习方式**：先看知识（一），再跑案例（二），然后看业务怎么用（三），跑不通查（四），最后自测（五）和总结（六）。

---

# 一、这一章讲什么

## 1.1 一次连接到底贵在哪

`pymysql.connect()` 不是"打开一个文件"，它至少做了四件事：

| 步骤 | 干什么 | 代价 |
| --- | --- | --- |
| ① TCP 三次握手 | 客户端连上 3306 | 一个网络往返 |
| ② 服务端握手 | MySQL 发版本、认证插件、salt | 又一个往返 |
| ③ 身份认证 | 客户端交凭据，MySQL 8 还要校验 RSA 公钥 | 计算 + 往返 |
| ④ 会话初始化 | 设字符集、时区、`sql_mode`、`autocommit` | 若干语句 |

四步走完才拿到一个"能执行 SQL"的连接，而执行一句 `SELECT 1` 可能只要 0.5 ms。**建连接的代价，比用连接大一个数量级。**

## 1.2 池子的三条规则

```plain
        启动时
          │
          ▼
   ┌──────────────┐   mincached=2，先建 2 条待命
   │  空闲连接池   │◄──────────────┐
   │  idle cache  │               │
   └──────┬───────┘               │
          │ ① connection() 借      │ ④ close() 还
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

| 规则 | 行为 |
| --- | --- |
| 借出时优先取空闲连接 | 有就复用，没有才新建 |
| 归还时超过 `maxcached` | 多出来的真关闭，避免闲置占资源 |
| 总数达到 `maxconnections` | `blocking=True` 阻塞，`False` 抛异常 |

## 1.3 五个参数，一句话一个

| 参数 | 一句话 | 常见值 |
| --- | --- | --- |
| `mincached` | 启动时预建几条待命 | 2 ~ 5 |
| `maxcached` | 空闲时最多留几条 | 同 `maxconnections` |
| `maxconnections` | 池子上限，超了就排队 | 并发峰值 ÷ 2 左右 |
| `blocking` | 池满时是等待还是报错 | Web 服务用 `True` |
| `ping` | 借出前探活，坏连接自动重建 | 设 `1` |

> 💡 `ping=1` 这一行能省掉一整类线上事故：MySQL 默认 `wait_timeout=28800`（8 小时），夜里没人访问，池里的连接全被服务端单方面掐断，第二天第一个请求拿到死连接，报 `Lost connection to MySQL server`。

> ⚠️ 池子是**进程内对象**。多进程部署时每个进程各有一份自己的池，不是共享的。

---

# 二、可执行案例

| 案例 | 文件 | 验证什么 | 用时 |
| --- | --- | --- | --- |
| 1 | `01_pool_basic.py` | 借还一次连接，连接是否被复用 | 2 分钟 |
| 2 | `02_benchmark.py` | 裸连接 vs 连接池，差多少倍 | 3 分钟 |

## 跑之前的准备

```bash
cd D:/github_repository/mysql-learning
export MYSQL_PASSWORD=你的密码
```

> 本章默认连 `test_db`（`pool.py` 里的默认库）。想换库就加 `export MYSQL_DATABASE=learn_mysql`。

---

## 案例 1 · 借一条，还一条

**验证什么**：`connection()` 到底是"新建"还是"借用"。

**文件**：`chapters/ch02/code/01_pool_basic.py`

**核心代码**：

```python
conn = get_conn()          # 借
try:
    with conn.cursor() as cur:
        cur.execute("SELECT CONNECTION_ID()")
        print(cur.fetchone())
finally:
    conn.close()           # 还，不是断
```

**怎么跑**：

```bash
python chapters/ch02/code/01_pool_basic.py
```

**你会看到**：

```plain
--- ① 借一条连接，查一句 ---
    查询结果: (1,)

--- ② 连续借三次，看连接 id 是否复用 ---
    三次借到的连接 id: [519, 520, 519]
    去重后只有 2 个 —— 正好是池子预建的连接数，没有新建

--- ③ 池子的上限 ---
    maxconnections = 10
    刚才 3 次借还都归还了，池子没有泄漏
```

> 连接 id 是 MySQL 的线程号，每次运行都不一样，但**去重后的个数**应该等于 `mincached`。

**能学到什么**：

- `close()` 在池化语境下是**归还**，不是断开——这是本章最重要的一句话
- 三次借还只用到 2 个线程号，说明连接一直在复用，没有重新握手
- 池子的连接数由 `mincached` 决定，不是每次借都新建

**改一改**（1 分钟）：把 `POOL_MIN_CACHED` 设成 4 再跑，看去重后的个数变成几。

```bash
POOL_MIN_CACHED=4 python chapters/ch02/code/01_pool_basic.py
```

---

## 案例 2 · 裸连接 vs 连接池，差多少

**验证什么**：省下来的建连开销，到底能变成多少时间。

**文件**：`chapters/ch02/code/02_benchmark.py`

**核心代码**：

```python
def query_once_raw():          # 裸连接：连上、查、断
    conn = pymysql.connect(**DB_CONFIG)
    ...
    conn.close()               # 真断 TCP

def query_once_pool():         # 池化：借、查、还
    conn = get_conn()
    ...
    conn.close()               # 归还
```

**怎么跑**：

```bash
python chapters/ch02/code/02_benchmark.py
```

**你会看到**（20 线程共 200 次查询）：

```plain
连接池上限 maxconnections=10

裸连接     200 次 / 20 线程    总耗时   2.280s    平均  11.40 ms/次
连接池     200 次 / 20 线程    总耗时   0.532s    平均   2.66 ms/次

连接池比裸连接快 4.3 倍
```

**能学到什么**：

- 11.40 ms 里，真正执行 `SELECT 1` 不到 0.5 ms，其余全是建连和断连
- 差距倍数和硬件有关，但**方向不会变**：并发越高、查询越短，池化收益越大
- 反过来说：如果你的查询本身要跑 500 ms，池化省的那几毫秒就不重要了——**先优化 SQL，再优化连接**

**改一改**（3 分钟）：把上限压到 2，再看数字。

```bash
POOL_MAX=2 python chapters/ch02/code/02_benchmark.py
```

预期：连接池变慢，因为 20 个线程抢 2 条连接，大部分时间在排队。想完再往下读。

> 💡 这个实验的意义：**连接池不是越大越好**。上限小于并发时，线程在排队；上限过大时，数据库那边的连接数会把你拖垮。中间那个值，要靠压测找。

---

# 三、业务场景对话

**Q：公司的池子该开多大？**

没有标准答案，有个估算公式：

```plain
需要的连接数 ≈ 并发请求数 × 单个请求持有连接的时间 ÷ 请求间隔
```

更实际的做法：`maxconnections` 先设成「数据库 `max_connections` 的 1/3」，压测跑一遍，看有没有阻塞、`SHOW PROCESSLIST` 里连接数是不是一直贴着上限。**贴着上限不下降，说明池子小了；常年空着一半，说明设大了。**

**Q：为什么凌晨之后第一个请求经常报 `Lost connection`？**

MySQL 默认 `wait_timeout = 28800` 秒（8 小时）。半夜没人访问，池子里的连接全被服务端单方面关掉，但池子以为它们还活着。第二天第一个请求拿到一条死连接。

修法就是 `ping=1`：每次借出前先发个 `SELECT 1` 探活，断了自动重建。代价是每次多几毫秒，换来不会莫名其妙 500。

**Q：多进程部署时，池子要怎么算？**

池子是**进程内对象**。4 个 worker 进程、每个 `maxconnections=10`，对 MySQL 来说就是 40 条连接。

所以算池子大小时要乘上进程数：

```plain
MySQL 侧最大连接数 = 进程数 × maxconnections
```

这个数必须明显小于 MySQL 的 `max_connections`（默认 151），否则高峰期会出现 `Too many connections`。

---

# 四、跑不起来怎么办

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `ModuleNotFoundError: dbutils` | 没装 DBUtils | `pip install DBUtils` |
| `ModuleNotFoundError: pool` | 没在脚本目录跑 | 从仓库根用完整路径执行 |
| `Access denied for user 'root'` | 密码没设或错 | `export MYSQL_PASSWORD=你的密码` |
| `Table 'xxx' doesn't exist` | 连错库 | 本章默认 `test_db`，要换就设 `MYSQL_DATABASE` |
| 卡住不动、无报错 | 连接泄漏，池被借空且 `blocking=True` | 检查每条借出是否都有 `close()` |
| `Too many connections` | 进程数 × 池上限超过 MySQL 限制 | 调小 `maxconnections` 或调大 `max_connections` |

---

# 五、自测：3 道面试题

### Q1. 什么是数据库连接池？为什么需要它？

> **满分回答模板**
>
> 一句话：**预先建好一组连接并复用，避免每次请求都做握手和认证**。
>
> 展开三点：
> 1. 建连接要 TCP 三次握手 + 认证 + 会话初始化，比执行一条简单 SQL 贵一个数量级；
> 2. 不池化的话，并发一高就把 MySQL 的 `max_connections` 打满，直接 `Too many connections`；
> 3. 池化同时解决两个问题：**复用省时间**，**限流保稳定**。
>
> 加分项：我们实测过，200 次查询 / 20 线程，裸连接 11.4 ms 一次，池化后 2.66 ms，差不多 4 倍。

### Q2. 连接池的核心参数怎么配？

> **满分回答模板**
>
> 一句话：**上限看并发，满时策略看业务，探活看稳定性**。
>
> 展开：
> - `maxconnections`：按「并发峰值 × 持有时间」估，且必须小于数据库的 `max_connections`；
> - `blocking`：Web 服务设 `True`（宁可排队也别 500），离线任务设 `False`（快速失败）；
> - `ping=1`：解决 `wait_timeout` 导致的死连接；
> - `mincached`：预热，服务启动后立刻有连接可用。
>
> 加分项：参数不是拍脑袋定的，要压测。我们做过把上限压到 2 的实验，20 个线程抢 2 条连接，耗时反而变长——**池子不是越大越好**。

### Q3. 池化之后，`close()` 还叫"关闭"吗？

> **满分回答模板**
>
> 一句话：**不是断开，是归还**。
>
> 展开：
> 1. 池化连接被包了一层，`close()` 把连接放回空闲队列，物理 TCP 连接仍然活着；
> 2. 所以"忘记 close 会泄漏"在池化语境下泄漏的是**租约**，不是 TCP 连接；
> 3. 借够 `maxconnections` 次没还，池子就空了，配合 `blocking=True` 会**无限期卡住**，而且不报错——这是最难查的一类故障。
>
> 加分项：SQLAlchemy 的 `Session.close()` 语义相同，也是归还连接。所以这句结论能直接套用到第三章。

---

# 六、本章总结

**三句话**：

1. 连接贵在建连，不在执行 SQL
2. 池化 = 复用 + 限流，一个省时间，一个保稳定
3. `close()` 是归还，忘记归还就卡死在 `blocking` 上

**验收清单**：

- [ ] 能说出一次 MySQL 连接要经历哪四步
- [ ] 能解释 `maxconnections`、`blocking`、`ping` 各自解决什么问题
- [ ] 能解释"忘记 close 会泄漏"泄漏的到底是什么
- [ ] 能估算「4 个 worker × 池上限 10」时 MySQL 侧要承受多少连接

**下一步**：第三章进入 SQLAlchemy ORM，Engine 内部就是一个连接池，本章的参数会以 `pool_size` / `max_overflow` 的形式再出现一次。

---

<small>相关：[第三章 -- SQLAlchemy ORM 基础](../../ch03/notes/SQLAlchemy%20ORM%20基础.md) · [改造前代码](../code/legacy/demo-user-manager-sys.py)</small>
