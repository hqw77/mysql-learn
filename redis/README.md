# 第三部分 · Redis 缓存

> 状态:**知识部分已完成,项目接入待开始**
> 前面八章的数据都直接压在 MySQL 上。这里引入 Redis,解决"读多写少"的性能问题。

## 环境

Redis 7.4 跑在 Docker 里:

```bash
docker run -d --name mysql-learn-redis \
  --restart unless-stopped \
  -p 6379:6379 \
  redis:7-alpine

docker exec mysql-learn-redis redis-cli ping    # → PONG
```

Python 客户端:`redis`(redis-py 8.1)。

## 章节目录

| 章 | 主题 | 状态 |
| --- | --- | --- |
| [ch01](ch01/notes/Redis%20基础.md) | Redis 基础:五种类型、过期、Python 操作 | ✅ 完成 |
| [ch02](ch02/notes/缓存设计与三大问题.md) | 缓存设计:Cache-Aside、穿透/击穿/雪崩、一致性 | ✅ 完成 |
| ch03 | 接入 `project/`:配置、连接池、缓存服务、失效、测试 | ⬜ 待开始 |

## 案例清单

| 文件 | 验证什么 |
| --- | --- |
| `ch01/code/01_connect.py` | 单连接 vs 连接池、`decode_responses` |
| `ch01/code/02_string_hash.py` | String 计数、`SET NX EX`、Hash 存对象 |
| `ch01/code/03_list_set_zset.py` | 队列/栈、集合运算、排行榜 |
| `ch01/code/04_expire_and_key.py` | TTL 三种返回值、SCAN、DEL/UNLINK、命名 |
| `ch02/code/01_cache_aside.py` | Cache-Aside 读写路径、命中率与耗时对比 |
| `ch02/code/02_three_problems.py` | 穿透/击穿/雪崩的复现与防护 |
| `ch02/code/03_consistency.py` | 先删缓存 vs 先改库的脏数据窗口 |

运行方式(在仓库根目录):

```bash
python redis/ch01/code/01_connect.py
python redis/ch02/code/03_consistency.py
```

所有案例自带 `demo:` 前缀,结束时会自行清理,不影响其他数据。

## 目录规范

与 `mysql_notes/` 一致:

```plain
redis/
├── README.md
├── chNN/
│   ├── notes/        # 笔记(教材骨架 + 通俗理解注解 + 案例引用)
│   └── code/         # 可运行案例,编号 NN_xxx.py
└── extras/notes/     # 番外
```

笔记格式见 [DOC-PATTERN](../docs/DOC-PATTERN.md)。

## 与工程的关系

ch03 会把缓存真实接进 `project/`:

```plain
project/app/core/config.py           加 redis 配置
project/app/db/redis_client.py       连接池
project/app/services/cache.py        get/set/delete 封装
project/app/services/user_cache.py   用户详情的 Cache-Aside
project/app/services/user_service.py 写操作后删缓存
project/tests/test_cache.py          命中与失效用例
```

## 一条设计原则

**缓存里存 DTO(`UserOut` 序列化后的 JSON),不存 ORM 对象。**

ORM 对象与 Session 绑定,取出后会变成 detached 实例,访问属性直接报错。ch03 会重点讲这条。

## 前置

- `project/` 能启动,`docker` 可用
- 了解分层结构(`routers → services → models`)
