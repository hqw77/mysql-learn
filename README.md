# mysql-learning

Python + MySQL 进阶实战学习仓库。

从写第一句 `SELECT` 开始，一路走到 SQLAlchemy ORM + FastAPI 分层应用。每一章都留下三样东西：**可运行的代码**、**能复现的实验数据**、**自己整理过的笔记**。

## 仓库怎么组织

每章一个父目录，**笔记和代码分开**：

```plain
chapters/ch01/
├── notes/     # 这一章的笔记（只有 .md）
└── code/      # 这一章的代码（只有 .py）
```

| 层 | 目录 | 是什么 | 现在到哪 |
| --- | --- | --- | --- |
| 章节包 | `chapters/chNN/` | 每章一个，内含 `notes/` 与 `code/` | 第一 ~ 三章 |
| 作品集 | `app/` | 最终要交付的 FastAPI 项目 | 第三章落地，等第四章长肉 |

> `app/` 既不是空壳，也不是成品。它现在能跑通健康检查、能查库，但**业务代码是第四章才开始写的**。

## 学习进度

| 章节 | 主题 | 状态 | 笔记 | 代码 |
| --- | --- | --- | --- | --- |
| 第一章 | MySQL 进阶基础（建表 / JOIN / 事务 / 索引 / 设计 / 运维） | 已完成 | `chapters/ch01/notes/` | `chapters/ch01/code/` + `sql/` |
| 第二章 | Python 数据库连接池 | 已完成 | `chapters/ch02/notes/` | `chapters/ch02/code/` |
| 第三章 | SQLAlchemy ORM 基础 | 已完成 | `chapters/ch03/notes/` | `chapters/ch03/code/` + `app/models/user.py` |
| 第四章 | SQLAlchemy ORM CRUD | 下一个 | — | — |
| 第五~七章 | 进阶 / FastAPI / 完整项目 | 待开始 | — | — |

## 目录结构

```plain
mysql-learning/
├── chapters/                     # 每一章：笔记与代码分开放
│   ├── README.md                 # 总纲：学习路线与各章目标
│   ├── ch01/
│   │   ├── notes/                # 阶段0 ~ 阶段7（8 篇笔记）
│   │   └── code/                 # phase0 ~ phase6（8 个脚本）
│   ├── ch02/
│   │   ├── notes/Python 数据库连接池.md
│   │   └── code/                 # pool.py / user_dao.py / benchmark.py
│   │       └── legacy/           # 最早的 PyMySQL 用户管理系统（改造对象）
│   ├── ch03/
│   │   ├── notes/SQLAlchemy ORM 基础.md
│   │   └── code/                 # 01~04 四个可执行案例
│   └── extras/                   # 番外：主线上放不下的专题
│       └── notes/01-Alembic 数据库迁移.md
├── app/                          # 作品集：第 4 章开始长出业务代码
│   ├── main.py                   # 入口：路由注册、异常处理、生命周期
│   ├── deps.py                   # 依赖注入出口（get_db）
│   ├── core/
│   │   ├── config.py             # 配置，读 .env
│   │   └── exceptions.py         # 业务异常 → HTTP 状态码
│   ├── db/
│   │   ├── base.py               # DeclarativeBase
│   │   ├── engine.py             # Engine + 连接池
│   │   └── session.py            # SessionLocal 与 get_db
│   ├── models/
│   │   └── user.py               # User → learn_mysql.users
│   └── routers/
│       └── health.py             # /health、/health/db
├── migrations/                   # Alembic 迁移（第三章产物）
│   ├── env.py                    # 从 .env 取连接串，include_object 防误删
│   └── versions/0001_initial_schema.py
├── sql/                          # 纯 SQL 脚本
│   └── user-manager-sys/         # 用户管理系统建库脚本
├── docs/                         # 架构说明 · 教程规划 · 文档排版模式
├── alembic.ini
├── .env.example
└── requirements.txt
```

> `app/schemas/`、`app/services/`、`tests/` 在第四章开工时再建，现在不占位——空目录只会让人以为废弃了。

## 快速开始

### 1. 环境

- Python 3.12
- MySQL 8.0（本仓库在 8.0.42 上验证）
- Windows / Git Bash

### 2. 安装依赖

```bash
python -m venv .venv
source .venv/Scripts/activate          # Windows CMD/PowerShell 用 .venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 国内网络直连 PyPI 经常卡住，加 `-i` 换清华镜像。

### 3. 配置数据库

```bash
cp .env.example .env
# 编辑 .env，填入真实密码
```

`.env` 已被 `.gitignore` 忽略，不会提交。**仓库内不含任何密码。**

### 4. 启动应用

```bash
uvicorn app.main:app --reload
```

| 地址 | 说明 |
| --- | --- |
| http://127.0.0.1:8000/docs | Swagger 接口文档 |
| http://127.0.0.1:8000/health | 进程存活探测（不碰数据库） |
| http://127.0.0.1:8000/health/db | 数据库连通探测，返回 MySQL 版本 |

## 应用分层

调用方向单向：`routers → services → models`。反向依赖一律视为设计错误。

| 层 | 只负责 | 禁止 |
| --- | --- | --- |
| `routers/` | HTTP 入参出参、状态码、依赖注入 | 写 SQL、写业务规则 |
| `services/` | 业务规则、事务提交与回滚 | 感知 HTTP、返回 Response |
| `models/` | 表结构映射、关系定义 | 业务判断 |
| `db/` | Engine / Session 生命周期 | 业务代码 |
| `core/` | 配置、安全、异常定义 | 依赖上层模块 |

## 笔记索引

### 第一章 · MySQL 进阶基础

| 阶段 | 主题 | 代码 |
| --- | --- | --- |
| [阶段0](chapters/ch01/notes/阶段0%20--%20环境搭建与连通.md) | 环境搭建与连通 | `chapters/ch01/code/phase0/` |
| [阶段1](chapters/ch01/notes/阶段1%20--%20单表%20CRUD%20与基础查询.md) | 单表 CRUD 与基础查询 | `chapters/ch01/code/phase1/` |
| [阶段2](chapters/ch01/notes/阶段2%20--%20建表进阶.md) | 建表进阶：类型、六大约束、规范 | `chapters/ch01/code/phase2/` |
| [阶段3](chapters/ch01/notes/阶段3%20--%20多表查询与%20JOIN.md) | 多表查询与 JOIN | `chapters/ch01/code/phase3/` |
| [阶段4](chapters/ch01/notes/阶段%204：事务与并发控制.md) | 事务与并发控制 | `chapters/ch01/code/phase4/` |
| [阶段5](chapters/ch01/notes/阶段5%20--%20索引与性能优化.md) | 索引与性能优化 | `chapters/ch01/code/phase5/` |
| [阶段6](chapters/ch01/notes/阶段6%20--%20数据库设计（范式与建模）.md) | 数据库设计：范式与建模 | `chapters/ch01/code/phase6/` |
| [阶段7](chapters/ch01/notes/阶段7%20--%20运维与架构.md) | 运维与架构 | — |

### 第二章 · Python 数据库连接池

| 主题 | 笔记 |
| --- | --- |
| 连接池原理、PooledDB 参数详解、压测对比、面试题 | [第二章 -- Python 数据库连接池](chapters/ch02/notes/Python%20数据库连接池.md) |

### 第三章 · SQLAlchemy ORM 基础

| 主题 | 笔记 | 代码 |
| --- | --- | --- |
| Engine / Base / Model / Session 四件套、`Mapped[T]` 与 `mapped_column`、脏检查机制、四个可执行案例 | [第三章](chapters/ch03/notes/SQLAlchemy%20ORM%20基础.md) | `chapters/ch03/code/01~04` + `app/models/user.py` |
| 建表迁移单独成篇：`create_all` 为什么不适用、Alembic 基线、`include_object` 防误删 | [番外01 -- Alembic 数据库迁移](chapters/extras/notes/01-Alembic%20数据库迁移.md) | `migrations/` |

完整学习路线见 [Python + MySQL 进阶实战教程](chapters/README.md)。

## 数据库迁移

表结构变更一律走 Alembic，不要用 `Base.metadata.create_all`。完整讲解见 [番外01](chapters/extras/notes/01-Alembic%20数据库迁移.md)。

```bash
alembic current                          # 当前版本
alembic check                            # 模型与库是否有差异
alembic revision --autogenerate -m "描述" # 生成迁移
alembic upgrade head                     # 应用迁移
alembic downgrade -1                     # 回退一步
```

> 注意：库里有第一章遗留的练习表（`students`/`books`/`orders`…），它们没有对应的 ORM 模型。
> `migrations/env.py` 里的 `include_object` 会把这些表排除在外，防止 autogenerate 生成 `DROP TABLE`。

## 练习代码怎么跑

所有 `chapters/*/code/` 下的脚本都通过环境变量读连接信息，先设置密码：

```bash
export MYSQL_PASSWORD=你的密码
```

| 脚本 | 作用 |
| --- | --- |
| `python chapters/ch01/code/phase0/check_connection.py` | 验证能否连通 MySQL |
| `python chapters/ch01/code/phase1/crud_basic.py` | 单表增删改查 |
| `python chapters/ch01/code/phase1/student_manager.py` | 控制台版学生管理（交互式） |
| `python chapters/ch01/code/phase2/create_tables.py` | 用 Python 执行 DDL |
| `python chapters/ch01/code/phase3/test_subquery.py` | 嵌套子查询 |
| `python chapters/ch01/code/phase4/transaction_test.py` | 转账事务与回滚 |
| `python chapters/ch01/code/phase5/test_explain.py` | EXPLAIN 前后对比索引效果 |
| `python chapters/ch01/code/phase6/design_check.py` | 查看当前库的表结构 |
| `python chapters/ch02/code/legacy/demo-user-manager-sys.py` | 裸连接版用户管理（改造前） |
| `python chapters/ch02/code/benchmark.py` | 裸连接 vs 连接池压测（改造后） |
| `python chapters/ch03/code/01_first_query.py` | 案例1：最小闭环，用 ORM 查出第一条数据 |
| `python chapters/ch03/code/02_pymysql_vs_orm.py` | 案例2：PyMySQL 拿字典 vs ORM 拿对象 |
| `python chapters/ch03/code/03_dirty_check.py` | 案例3：脏检查，验证什么时候才发 UPDATE |
| `python chapters/ch03/code/04_use_app_model.py` | 案例4：工程版模型，和脚本版只差一个 import |

### 第二章实测数据

200 次查询 / 20 线程：

```plain
裸连接     总耗时 2.366s    平均 11.83 ms/次
连接池     总耗时 0.556s    平均  2.78 ms/次
连接池比裸连接快 4.3 倍
```

## 技术栈

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| MySQL | 8.0.42 | 数据库 |
| PyMySQL | 1.2.3 | 原生驱动 |
| DBUtils | 3.2.0 | 连接池（第二章） |
| SQLAlchemy | 2.1.6 | ORM 与连接池（应用层） |
| FastAPI | 0.162.0 | Web 框架 |
| uvicorn | 0.54.0 | ASGI 服务器 |
| pydantic-settings | 2.16.2 | 配置管理 |

## 约定

- **密码一律走环境变量 / `.env`**，代码里不出现明文。
- `.env`、`.venv/`、`__pycache__/` 均已加入 `.gitignore`。
- 每章一个目录：`chapters/chNN/`，里面 `notes/` 只放 `.md`，`code/` 只放 `.py`。
- 应用代码与学习代码分离：`app/` 是作品集，`chapters/` 是学习轨迹，两者不互相 import。
- 目录只在有内容时才建，不留空包。

## 常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| `mysql: command not found` | PATH 没生效，重启 VSCode 让新环境变量生效 |
| `detected dubious ownership` | 目录属主与当前用户不一致，执行 `git config --global --add safe.directory 仓库路径` |
| `pip install` 卡住 | 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `Access denied for user 'root'` | `.env` 里的 `MYSQL_PASSWORD` 不对 |
| `Lost connection to MySQL server` | 连接被 `wait_timeout` 断开，连接池设 `ping=1` |
