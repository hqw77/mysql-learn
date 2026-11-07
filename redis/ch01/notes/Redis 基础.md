# Redis 第一章 · Redis 基础

## 1.1 学习目标

本章讲清 Redis 本身,为后面的"在项目里加缓存"打底,具体包括：

1. 理解 Redis 是什么、和 MySQL 的分工区别
2. 掌握五种数据类型及各自的典型用途
3. 掌握过期时间与 key 的命名、遍历、删除
4. 能够用 Python 连接 Redis,理解连接池与 `decode_responses`
5. 知道哪些操作会踩坑（如对小数做 `HINCRBY`）

前置知识：无。有 MySQL 使用经验更容易理解。

> **本章的读法**：正文是教材写法,每个关键概念后面有一个「通俗理解」框。
> 本章四个案例都是独立脚本,不依赖 `project/`,直接在仓库根目录运行。

---

## 1.2 为什么需要 Redis

### 1.2.1 一个请求慢在哪

假设一个用户详情接口,数据在 MySQL 里：

```plain
   请求进来
      │
      ├─ 建立/借出数据库连接       ~1 ms
      ├─ 发 SQL、网络往返          ~1 ms
      ├─ MySQL 解析、执行、返回     ~1~5 ms
      └─ 序列化成 JSON             ~0.5 ms
      ────────────────────────────────────
      合计 3~8 ms,并发一高就排队
```

数据量再大、加再多连接池,也改变不了"每次都要去磁盘上找"这件事。

### 1.2.2 缓存省掉的是什么

Redis 把结果放在**内存**里：

```plain
   第一次请求：查 MySQL → 写入 Redis → 返回        8 ms
   之后请求：  直接读 Redis → 返回                 0.3 ms
```

省掉的是"查数据库"这一整段,不是网络往返。

> **通俗理解**：MySQL 是仓库,东西全但取货慢；Redis 是收银台旁边的小货架,只放最常卖的那几样。顾客要什么,先看货架,没有再去仓库拿,拿完顺手摆上货架。

### 1.2.3 Redis 与 MySQL 的分工

| | MySQL | Redis |
| --- | --- | --- |
| 存储位置 | 磁盘 | 内存 |
| 数据量 | GB ~ TB | GB 级（受内存限制） |
| 读写速度 | 毫秒级 | 微秒级 |
| 是否持久化 | 天然持久 | 可选（RDB/AOF）,但可能丢数据 |
| 定位 | **唯一可信来源** | **加速层,丢了可以重建** |

**这条最重要**：Redis 里的数据必须能从 MySQL 重建。凡是"只存在 Redis、丢了就没了"的数据,不该只用 Redis 存。

---

## 1.3 Redis 是什么

Redis 是一个**内存键值数据库**,同时支持持久化、发布订阅、事务、Lua 脚本。

三个关键特征：

| 特征 | 含义 | 影响 |
| --- | --- | --- |
| 数据在内存 | 读写不碰磁盘 | 快,但内存贵 |
| 单线程处理命令 | 命令排队执行,不会并发改同一份数据 | 单条命令原子,不用担心锁 |
| 支持多种数据结构 | 不只是 key-value 字符串 | 能直接表达列表、集合、排行榜 |

### 1.3.1 单线程为什么还快

因为它**不做磁盘 IO、不做复杂计算**,瓶颈在网络和内存,不在 CPU。单线程反而省掉了线程切换和加锁的开销。

> **通俗理解**：一个窗口只开一个收银员,但每笔交易只要 1 微秒。开十个收银员反而要协调谁先谁后,不如一个手快的。

### 1.3.2 版本与部署

本仓库用 Docker 跑 Redis 7：

```bash
docker run -d --name mysql-learn-redis \
  --restart unless-stopped \
  -p 6379:6379 \
  redis:7-alpine

docker exec mysql-learn-redis redis-cli ping    # → PONG
```

---

## 1.4 五种数据类型

### 1.4.1 String：单值与计数器

最基础的类型,值可以是字符串、数字、二进制。

```python
r.set("user:1:name", "张三")
r.get("user:1:name")            # '张三'
r.incr("page:visits")           # 原子 +1
r.set("lock:order:88", "A", nx=True, ex=10)    # 不存在才写
```

典型用途：

| 场景 | 命令 |
| --- | --- |
| 缓存一个对象（JSON 字符串） | `SET` / `GET` |
| 计数器（访问量、点赞数） | `INCR` / `INCRBY` |
| 分布式锁 | `SET key value NX EX 10` |
| 会话令牌 | `SET token xxx EX 3600` |

**`INCR` 是原子操作**,多个客户端同时加不会丢更新——这一点和第五章讲的"读出来改属性"完全不同。

### 1.4.2 Hash：对象的多个字段

一个 key 下存多组 field-value,适合存"对象",且可以只改其中一个字段。

```python
r.hset("user:1", mapping={"username": "张三", "points": "0"})
r.hget("user:1", "username")     # '张三'
r.hincrby("user:1", "points", 12)
r.hgetall("user:1")              # {'username': '张三', 'points': '12'}
```

### 1.4.3 List：队列与栈

有序、可重复,两端都能进出。

| 用法 | 组合 | 效果 |
| --- | --- | --- |
| 队列（FIFO） | 右进 `RPUSH` + 左出 `LPOP` | 先进先出 |
| 栈（LIFO） | 右进 `RPUSH` + 右出 `RPOP` | 后进先出 |
| 最近 N 条 | `LPUSH` + `LTRIM 0 4` | 只留最新 5 条 |

`LTRIM` 这个组合很实用：日志、消息流只保留最近若干条,不会无限增长。

### 1.4.4 Set：去重与集合运算

无序、自动去重,支持交并差。

```python
r.sadd("tag:a", "python", "mysql")
r.sadd("tag:b", "python", "docker")
r.sinter("tag:a", "tag:b")       # {'python'} 共同标签
r.sismember("tag:a", "python")   # 1
```

典型用途：文章标签、点赞去重、共同好友、抽奖池。

### 1.4.5 ZSet：排行榜

每个成员带一个分数,按分数自动排序。

```python
r.zadd("rank", {"张三": 888, "李四": 400})
r.zrevrange("rank", 0, 2, withscores=True)   # 前三名
r.zrank("rank", "李四")                       # 排名（从 0 开始）
r.zincrby("rank", 50, "王五")                 # 加分
```

> **通俗理解**：Set 是"谁在名单里",ZSet 是"谁排第几"。凡是需要"按分数排序"的,都用 ZSet——排行榜、延时队列、热搜。

### 1.4.6 五种类型速查

| 类型 | 一句话 | 常用命令 |
| --- | --- | --- |
| String | 单值、计数、锁 | `set/get/incr/setnx` |
| Hash | 对象的多个字段 | `hset/hget/hincrby` |
| List | 队列、栈、最近 N 条 | `lpush/rpop/ltrim` |
| Set | 去重、标签、交集 | `sadd/sinter/sismember` |
| ZSet | 排行榜、延时队列 | `zadd/zrevrange/zrank` |

案例文件：

- `redis/ch01/code/02_string_hash.py`
- `redis/ch01/code/03_list_set_zset.py`

真实运行结果（节选）：

```plain
--- ② 计数器:INCR 是原子操作 ---
    初始: 100
    INCR: 101
    INCRBY 10: 111
    DECRBY 5 : 106
    → 全程不需要先读再写,不会丢更新

--- ④ SET NX / XX：只有不存在才写（分布式锁的雏形） ---
    第一次（key 不存在）: True
    第二次（key 已存在）: None  → 抢锁失败
    剩余 TTL: 10 秒

--- ⑤ ZSet：按分数排序 = 排行榜 ---
    正序（分数低的在前）: [('王五', 100.0), ('李四', 400.0), ('张三', 888.0)]
    倒序（榜单前三）: [('张三', 888.0), ('李四', 400.0), ('王五', 100.0)]
    李四的排名（从 0 开始）: 1
```

---

## 1.5 过期与 key 管理

### 1.5.1 设置过期

```python
r.set("code", "8888", ex=60)      # 秒
r.set("code", "8888", px=5000)    # 毫秒
r.expire("session", 30)           # 给已有 key 设置
```

`SET` 时直接带 `ex` 是最推荐的做法——一步完成,不会有"设置了值但忘了设过期"的窗口。

### 1.5.2 TTL 的三种返回值

| 返回值 | 含义 |
| --- | --- |
| `-2` | key 不存在（或已过期） |
| `-1` | 存在,但没有过期时间（永不过期） |
| 正整数 | 剩余秒数 |

> **通俗理解**：`-1` 是个危险信号。缓存 key 如果返回 `-1`,说明它永远不会过期,内存会被慢慢吃光。

### 1.5.3 过期不是"到点就消失"

Redis 用两种策略清理过期 key：

1. **惰性删除**：你访问时才检查,过期了就删；
2. **定期抽样**：每秒随机抽一些 key 检查。

所以 key 过期后,内存不会立刻释放。

案例 4 的实测：

```plain
--- ⑤ 过期是被动的：到点不会立刻消失 ---
    设置 300ms 后: v
    等 0.5 秒后 : None  → 已过期
    TTL: -2  → -2（key 不存在）
```

### 1.5.4 遍历：用 SCAN 不用 KEYS

```python
for key in r.scan_iter("user:*"):
    print(key)
```

**`KEYS` 会一次性扫描全部 key,key 多时直接阻塞服务**（单线程,扫多久就卡多久）。生产环境一律用 `SCAN`。

### 1.5.5 删除：DEL 与 UNLINK

| 命令 | 行为 | 何时用 |
| --- | --- | --- |
| `DEL` | 同步删除,删完才返回 | 小 key |
| `UNLINK` | 只解除引用,后台线程回收内存 | 大 key（几十万元素） |

### 1.5.6 命名规范

```plain
业务:对象:标识          user:42   order:2024:88   article:1001:views
带环境前缀              prod:user:42    dev:user:42
```

好处是可以用 `SCAN user:*` 批量管理,也能一眼看出是哪个业务的数据。

案例文件：`redis/ch01/code/04_expire_and_key.py`

真实运行结果：

```plain
--- ③ TTL 的三种返回值 ---
    key 不存在: -2  → -2
    key 无过期: -1  → -1
    有过期     : 60  → 剩余秒数

--- ⑥ SCAN：遍历 key 的正确方式 ---
    SCAN 匹配到: ['demo:ttl:item:0', 'demo:ttl:item:1', ...]
```

---

## 1.6 用 Python 操作 Redis

### 1.6.1 安装与连接

```bash
pip install redis
```

```python
import redis

# 方式一：单连接（每次 new 一个）
r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)

# 方式二：连接池（推荐,全进程一份）
pool = redis.ConnectionPool(host="127.0.0.1", port=6379, db=0,
                            decode_responses=True, max_connections=20)
client = redis.Redis(connection_pool=pool)
```

和第二章的 MySQL 连接池是同一个道理：**建立网络连接很贵,复用才划算**。

### 1.6.2 decode_responses

```python
redis.Redis(...)                        # 默认 False,get 返回 bytes
redis.Redis(..., decode_responses=True) # 返回 str
```

实测：

```plain
    decode=False -> b'\xe4\xb8\xad\xe6\x96\x87\xe5\x80\xbc'  (bytes)
    decode=True  -> 中文值  (str)
```

> **通俗理解**：Redis 里存的本来就是字节。`decode_responses=True` 就是让客户端自动帮你解码成字符串,省得每处都写 `.decode()`。

### 1.6.3 存对象：JSON 序列化

Redis 只能存字符串/字节,存一个 dict 或 ORM 对象必须先序列化：

```python
import json

r.set("user:42", json.dumps({"id": 42, "name": "张三"}, ensure_ascii=False), ex=300)
data = json.loads(r.get("user:42"))
```

**注意**：`ensure_ascii=False` 让中文原样存储,否则会变成 `\u5f20\u4e09`,用 `redis-cli` 看的时候很难受。

案例文件：`redis/ch01/code/01_connect.py`

真实运行结果：

```plain
--- ② 连接池：全进程一份,反复复用 ---
    PING: True
    池子最大连接数: 20

--- ③ 服务端信息 ---
    Redis 版本: 7.4.11
    运行模式  : standalone
    已用内存  : 1.13M
```

---

## 1.7 常见错误

| 错误信息 | 原因 | 解决方法 |
| --- | --- | --- |
| `ConnectionRefusedError` | Redis 没启动 | `docker start mysql-learn-redis` |
| `redis.exceptions.ResponseError: hash value is not an integer` | 对小数做 `HINCRBY` | 整数用 `HINCRBY`,金额用 String 在应用层算 |
| `TypeError: Object of type bytes is not JSON serializable` | 忘了 `decode_responses=True` | 连接时加该参数,或手动 `.decode()` |
| `WRONGTYPE Operation against a key holding the wrong kind of value` | 同一个 key 先当 String 又当 Hash | key 的命名要能区分类型,必要时加后缀 |
| 内存一直涨 | key 没有设过期 | 所有缓存 key 必须带 TTL |
| 线上突然卡顿 | 用了 `KEYS *` | 改用 `SCAN` |
| `InsecureKeyLengthWarning` 之类忽略 | 与本项目无关（JWT 的警告） | — |

---

## 1.8 本章小结

1. Redis 是内存键值库,定位是**加速层**,数据必须能从 MySQL 重建。
2. 五种类型各有分工：String 存值与计数、Hash 存对象、List 做队列、Set 去重、ZSet 排行。
3. `INCR` / `HINCRBY` 是原子操作,天然避免丢更新；但只支持整数。
4. 缓存 key 必须带 TTL；`TTL` 返回 `-1` 意味着永不过期,是隐患。
5. 遍历 key 用 `SCAN`,不要用 `KEYS`；大 key 用 `UNLINK` 删除。
6. Python 侧用连接池 + `decode_responses=True`；存对象用 `json.dumps(..., ensure_ascii=False)`。

---

## 1.9 练习

1. 用 String 实现一个"同一用户 60 秒内只能发一次验证码"的限制（提示：`SET NX EX`）。
2. 用 ZSet 实现一个"最近 24 小时热榜",要求能取出前 10 名,并说明过期怎么处理。
3. 用 List 实现一个"只保留最近 100 条日志"的结构,写出压入与裁剪的命令。
4. 思考：如果 Redis 重启导致缓存全丢,你的系统会出现什么问题？哪些数据不能只放 Redis？

---

<small>相关:[第二章 -- 缓存设计与三大问题](../../ch02/notes/缓存设计与三大问题.md) · [返回 Redis 目录](../../README.md)</small>
