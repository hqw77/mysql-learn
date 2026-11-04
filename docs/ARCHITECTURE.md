# 项目架构

> 生成时间：2026-11-04 · 对应提交 `8e65f2c`
> 说明：`app/` 是工程代码，`practice/` 是学习轨迹，两者互不 import。

## 1. 全貌

```plain
┌──────────────────────────── mysql-learning（学习仓库）────────────────────────────┐
│                                                                                  │
│   ┌────────────────────────┐              ┌────────────────────────┐             │
│   │  app/  工程代码         │              │  practice/ 学习轨迹     │             │
│   │  FastAPI 分层应用       │              │  按阶段归档的独立脚本    │             │
│   │  （建设中）             │              │  phase0 ~ phase6        │             │
│   └───────────┬────────────┘              └───────────┬────────────┘             │
│               │                                       │                          │
│        SQLAlchemy 2.x                          PyMySQL / DBUtils                  │
│        Engine + Session                        PooledDB                          │
│               │                                       │                          │
│               └──────────────┬────────────────────────┘                          │
│                              ▼                                                   │
│                    ┌───────────────────┐                                         │
│                    │   MySQL 8.0.42    │                                         │
│                    │ learn_mysql       │                                         │
│                    │ test_db           │                                         │
│                    └───────────────────┘                                         │
│                                                                                  │
│   支撑材料：notes/（学习笔记）  sql/（建表造数脚本）  docs/（本文档）              │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## 2. 应用分层（app/）

调用方向**单向向下**，反向依赖视为设计错误。

```plain
                        客户端（curl / Swagger UI / 前端）
                                    │ HTTP
                                    ▼
                    ┌───────────────────────────────┐
                    │  uvicorn  (ASGI Server)       │
                    └───────────────┬───────────────┘
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  app/main.py            ✅ 已实现                      │
        │    · FastAPI 实例                                     │
        │    · lifespan：启动预热 / 关闭时 engine.dispose()      │
        │    · exception_handler：AppError → {"detail": ...}     │
        │    · include_router()                                 │
        └───────────────────────────┬───────────────────────────┘
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  app/routers/*          ⚠️ 仅有 health.py              │
        │    入参校验 · 状态码 · Depends(get_db)                 │
        │    禁止：写 SQL、写业务规则                             │
        └───────────────────────────┬───────────────────────────┘
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  app/services/*         ❌ 空，待第三章/四章填充        │
        │    业务规则 · 事务边界 · 抛 AppError                   │
        └───────────────────────────┬───────────────────────────┘
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  app/models/*           ❌ 空，待第三章                 │
        │    SQLAlchemy 实体映射                                 │
        └───────────────────────────┬───────────────────────────┘
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  app/db/session.py      ✅ SessionLocal + get_db       │
        │  app/db/engine.py       ✅ Engine + QueuePool          │
        │  app/db/base.py         ✅ DeclarativeBase             │
        └───────────────────────────┬───────────────────────────┘
                                    ▼
                              MySQL 8.0.42
```

**旁路依赖**（不是调用链，是横切关注点）：

| 模块 | 谁在用 | 作用 |
| --- | --- | --- |
| `app/core/config.py` | `db/engine.py` | 读 `.env`，输出连接串与池参数 |
| `app/core/exceptions.py` | `services/`（未来）、`main.py` | 业务异常定义 → 统一 HTTP 映射 |
| `app/deps.py` | `routers/` | 依赖出口，隔离 router 与 db |

## 3. 一次 `/health/db` 请求的完整链路

```plain
① 客户端 GET /health/db
        │
②      ▼  uvicorn 收到请求，交给 FastAPI
        │
③      ▼  app/main.py 路由匹配 → health 路由
        │
④      ▼  app/routers/health.py::health_db(db: Session = Depends(get_db))
        │     FastAPI 解析 Depends，调用 get_db()
        │
⑤      ▼  app/deps.py → app/db/session.py::get_db()
        │     SessionLocal() 从连接池取一条连接
        │
⑥      ▼  app/db/engine.py::engine（QueuePool，pool_pre_ping=True）
        │
⑦      ▼  SQLAlchemy → PyMySQL → TCP 3306
        │
⑧      ▼  MySQL 执行 SELECT VERSION()
        │
⑨      ▼  结果逐层返回，finally 中 db.close() 把连接还给池
        │
⑩      ▼  JSONResponse {"status": "ok", "mysql_version": "8.0.42"}
```

## 4. 两条数据访问路径

仓库里同时存在两套访问方式，这是刻意的：`practice/` 用裸驱动理解原理，`app/` 用 ORM 做工程。

| 维度 | practice 路径 | app 路径 |
| --- | --- | --- |
| 驱动 | PyMySQL 直连 / DBUtils.PooledDB | SQLAlchemy + PyMySQL |
| 连接池 | 手写 `PooledDB(...)` | `create_engine` 自带 `QueuePool` |
| 池参数 | `mincached` / `maxcached` / `maxconnections` / `blocking` / `ping` | `pool_size` / `max_overflow` / `pool_recycle` / `pool_pre_ping` |
| 事务 | `conn.commit()` / `rollback()` | `Session.commit()` / `rollback()` |
| 代表文件 | `practice/ch02-pool/pool.py` | `app/db/engine.py` |

第二章的结论在这里直接复用：**`close()` 在池化语境下是归还，不是断开**。SQLAlchemy 的 `Session.close()` 同理，归还连接但不销毁池。

## 5. 数据库现状

### learn_mysql（第一 ~ 二章练习）

| 表 | 行数 | 用途 |
| --- | --- | --- |
| `students` | 4 | 单表 CRUD |
| `users` / `orders` / `order_items` / `products` | 3 / 3 / 4 / 3 | 多表关联与事务 |
| `books` / `authors` / `readers` / `borrows` | 0 | JOIN 练习（图书借阅模型） |
| `tags` | 0 | 多对多 |
| `big_users` | 99,822 | 索引与 EXPLAIN 压测 |

### test_db（第二章改造对象）

| 表 | 行数 | 用途 |
| --- | --- | --- |
| `user` / `role` / `user_role` | 3 / 3 / 4 | 用户-角色 RBAC |
| `articles` / `categories` / `comments` / `tags` / `article_tags` | 0 | 博客建模练习 |
| `blog_users` | 0 | 博客用户 |
| `orders` | 3 | 订单 |
| `big_users` | 100,239 | 索引压测 |

## 6. 完成度

| 层 | 文件 | 状态 | 对应章节 |
| --- | --- | --- | --- |
| 配置 | `core/config.py` | ✅ | 第三章 |
| 异常 | `core/exceptions.py` | ✅ | 第六章 |
| 连接 | `db/engine.py`、`db/session.py`、`db/base.py` | ✅ | 第三章 |
| 路由 | `routers/health.py` | ✅ 探针 | 第六章 |
| 路由 | `routers/users.py` 等 | ❌ | 第六、七章 |
| 模型 | `models/*` | ❌ 空 | 第三章 |
| 校验 | `schemas/*` | ❌ 空 | 第六章 |
| 业务 | `services/*` | ❌ 空 | 第四、五章 |
| 迁移 | `migrations/`（Alembic） | ❌ 未建 | 第五章 |
| 测试 | `tests/` | ❌ 空 | 第七章 |

## 7. Mermaid 版本（GitHub 直接渲染）

```mermaid
flowchart TD
    client["客户端<br/>curl / Swagger UI"]
    uvicorn["uvicorn<br/>ASGI Server"]
    main["app/main.py<br/>FastAPI 实例 + 异常处理"]
    router["app/routers/*<br/>HTTP 层"]
    deps["app/deps.py<br/>依赖出口"]
    session["app/db/session.py<br/>SessionLocal / get_db"]
    engine["app/db/engine.py<br/>Engine + QueuePool"]
    db[("MySQL 8.0.42<br/>learn_mysql / test_db")]

    services["app/services/*<br/>业务层（待建）"]
    models["app/models/*<br/>ORM（待建）"]
    config["app/core/config.py<br/>读 .env"]
    exceptions["app/core/exceptions.py"]

    client -->|HTTP| uvicorn
    uvicorn --> main
    main --> router
    router --> deps
    deps --> session
    session --> engine
    engine -->|PyMySQL| db

    router -.->|下一章接入| services
    services -.-> models
    models -.-> session

    config -->|连接串 / 池参数| engine
    exceptions -.-> services
    exceptions -.-> main

    style services stroke-dasharray: 5 5
    style models stroke-dasharray: 5 5
```

```mermaid
flowchart LR
    subgraph repo["mysql-learning"]
        direction TB
        app["app/<br/>工程代码"]
        practice["practice/<br/>学习轨迹"]
        notes["notes/<br/>笔记"]
        sql["sql/<br/>建表造数"]
    end

    app -->|SQLAlchemy| mysql[("MySQL")]
    practice -->|PyMySQL / PooledDB| mysql
    sql -->|DDL / DML| mysql
    notes -.->|对应讲解| app
    notes -.->|对应讲解| practice
```

## 8. 演进路线

```plain
当前 ──► 第三章：models/user.py + Alembic 基线
          ──► 第四章：services + routers，用户 CRUD
          ──► 第五章：relationship + RBAC（roles / permissions / user_roles）
          ──► 第六章：RESTful API + Pydantic 校验 + 分页
          ──► 第七章：认证、测试、完整项目收口
```

`app/` 当前是**可运行的骨架**：能起服务、能连库、能返回探针结果，但还没有业务表映射。从第三章开始才往里填肉。
