# 第三部分 · Redis 缓存

> 状态:**进行中**
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

## 计划内容

| 章 | 主题 | 说明 |
| --- | --- | --- |
| ch01 | Redis 基础与缓存入门 | 为什么缓存、五种数据结构、连接与常用命令 |
| ch02 | 在项目里加缓存 | Cache-Aside 模式、DTO 缓存、写操作失效 |
| ch03 | 缓存的三个经典问题 | 穿透、击穿、雪崩及各自应对 |
| ch04 | 缓存与一致性 | 先删还是后删、延迟双删、TTL 抖动 |

## 目录规范

与 `mysql_notes/` 一致:

```plain
redis/
├── README.md
├── chNN/
│   ├── notes/        # 笔记(教材骨架 + 通俗理解注解 + 案例引用)
│   └── code/         # 可运行案例
└── extras/notes/     # 番外
```

## 与工程的关系

Redis 不是玩具 demo,要真实接进 `project/`:

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

ORM 对象与 Session 绑定,取出后会变成 detached 实例,访问属性直接报错。这一条会在正文里重点讲。

## 前置

- `project/` 能启动,`docker` 可用
- 了解分层结构(`routers → services → models`)
