# mysql-learning

Python + MySQL 进阶实战学习仓库。

从写第一句 `SELECT` 开始，一路走到 SQLAlchemy ORM + FastAPI 分层应用。每一章都留下三样东西：**可运行的代码**、**能复现的实验数据**、**自己整理过的笔记**。

## 学习进度

| 章节 | 主题 | 状态 | 产出 |
| --- | --- | --- | --- |
| 第一章 | MySQL 进阶基础（建表 / JOIN / 事务 / 索引 / 设计 / 运维） | 已完成 | `notes/ch01/` + `practice/phase0~6/` + `sql/` |
| 第二章 | Python 数据库连接池 | 已完成 | `notes/第二章` + `practice/ch02-pool/` |
| 第三章 | SQLAlchemy ORM 基础 | 进行中 | `app/models/`、`app/db/` |
| 第四~七章 | ORM CRUD / 进阶 / FastAPI / 完整项目 | 待开始 | `app/services/`、`app/routers/` |

## 目录结构

```plain
mysql-learning/
├── app/                          # FastAPI 应用（按职责分层，正在建设中）
│   ├── main.py                   # 入口：路由注册、异常处理、生命周期
│   ├── deps.py                   # 依赖注入出口（get_db 等）
│   ├── core/
│   │   ├── config.py             # 全部配置，读 .env，禁止硬编码
│   │   └── exceptions.py         # 业务异常，统一映射 HTTP 状态码
│   ├── db/
│   │   ├── base.py               # DeclarativeBase，Alembic 的入口
│   │   ├── engine.py             # Engine + 连接池参数
│   │   └── session.py            # SessionLocal 与 get_db
│   ├── models/                   # SQLAlchemy ORM 实体（待填）
│   ├── schemas/                  # Pydantic 请求/响应模型（待填）
│   ├── services/                 # 业务逻辑与事务边界（待填）
│   └── routers/                  # HTTP 路由
│       └── health.py             # /health、/health/db
├── notes/                        # 学习笔记
│   ├── ch01/                     # 第一章：阶段0 ~ 阶段7
│   ├── 第二章 -- Python 数据库连接池.md
│   └── Python + MySQL 进阶实战教程.md
├── practice/                     # 学习过程的脚本，保留演进轨迹
│   ├── phase0/ ~ phase6/         # 对应 ch01 各阶段
│   ├── legacy/                   # 最早的 PyMySQL 用户管理系统（第二章的改造对象）
│   └── ch02-pool/                # 池化版：pool.py / user_dao.py / benchmark.py
├── sql/                          # 独立 SQL 脚本（建表、造数、练习题）
├── tests/                        # 自动化测试
├── .env.example
└── requirements.txt
```

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
| [阶段0](notes/ch01/阶段0%20--%20环境搭建与连通.md) | 环境搭建与连通 | `practice/phase0/` |
| [阶段1](notes/ch01/阶段1%20--%20单表%20CRUD%20与基础查询.md) | 单表 CRUD 与基础查询 | `practice/phase1/` |
| [阶段2](notes/ch01/阶段2%20--%20建表进阶.md) | 建表进阶：类型、六大约束、规范 | `practice/phase2/` |
| [阶段3](notes/ch01/阶段3%20--%20多表查询与%20JOIN.md) | 多表查询与 JOIN | `practice/phase3/` |
| [阶段4](notes/ch01/阶段%204：事务与并发控制.md) | 事务与并发控制 | `practice/phase4/` |
| [阶段5](notes/ch01/阶段5%20--%20索引与性能优化.md) | 索引与性能优化 | `practice/phase5/` |
| [阶段6](notes/ch01/阶段6%20--%20数据库设计（范式与建模）.md) | 数据库设计：范式与建模 | `practice/phase6/` |
| [阶段7](notes/ch01/阶段7%20--%20运维与架构.md) | 运维与架构 | — |

### 第二章 · Python 数据库连接池

| 主题 | 笔记 |
| --- | --- |
| 连接池原理、PooledDB 参数详解、压测对比、面试题 | [第二章 -- Python 数据库连接池](notes/第二章%20--%20Python%20数据库连接池.md) |

完整学习路线见 [Python + MySQL 进阶实战教程](notes/Python%20+%20MySQL%20进阶实战教程.md)。

## 练习代码怎么跑

所有 `practice/` 下的脚本都通过环境变量读连接信息，先设置密码：

```bash
export MYSQL_PASSWORD=你的密码
```

| 脚本 | 作用 |
| --- | --- |
| `python practice/phase0/check_connection.py` | 验证能否连通 MySQL |
| `python practice/phase1/crud_basic.py` | 单表增删改查 |
| `python practice/phase1/student_manager.py` | 控制台版学生管理（交互式） |
| `python practice/phase2/create_tables.py` | 用 Python 执行 DDL |
| `python practice/phase3/test_subquery.py` | 嵌套子查询 |
| `python practice/phase4/transaction_test.py` | 转账事务与回滚 |
| `python practice/phase5/test_explain.py` | EXPLAIN 前后对比索引效果 |
| `python practice/phase6/design_check.py` | 查看当前库的表结构 |
| `python practice/legacy/demo-user-manager-sys.py` | 裸连接版用户管理（改造前） |
| `python practice/ch02-pool/benchmark.py` | 裸连接 vs 连接池压测（改造后） |

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
- 笔记按章节目录组织（`notes/ch01/`…），练习代码按学习阶段归档（`practice/phaseN/`）。
- 应用代码与练习代码分离：`app/` 是工程产物，`practice/` 是学习轨迹，两者不互相 import。

## 常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| `mysql: command not found` | PATH 没生效，重启 VSCode 让新环境变量生效 |
| `detected dubious ownership` | 目录属主与当前用户不一致，执行 `git config --global --add safe.directory 仓库路径` |
| `pip install` 卡住 | 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `Access denied for user 'root'` | `.env` 里的 `MYSQL_PASSWORD` 不对 |
| `Lost connection to MySQL server` | 连接被 `wait_timeout` 断开，连接池设 `ping=1` |
