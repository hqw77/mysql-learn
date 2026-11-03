# mysql-learning

Python + MySQL 进阶实战学习仓库。从 SQL 基础一路走到 SQLAlchemy ORM + FastAPI 分层应用。

## 目录结构

```plain
mysql-learning/
├── app/                    # 应用代码（按职责分层）
│   ├── main.py             # FastAPI 入口：路由注册、异常处理、生命周期
│   ├── deps.py             # 依赖注入出口（get_db 等）
│   ├── core/
│   │   ├── config.py       # 全部配置，读 .env，禁止硬编码
│   │   └── exceptions.py   # 业务异常，统一映射 HTTP 状态码
│   ├── db/
│   │   ├── base.py         # DeclarativeBase，Alembic 的入口
│   │   ├── engine.py       # Engine + 连接池参数
│   │   └── session.py      # SessionLocal 与 get_db 生成器
│   ├── models/             # SQLAlchemy ORM 实体
│   ├── schemas/            # Pydantic 请求/响应模型
│   ├── services/           # 业务逻辑与事务边界
│   └── routers/            # HTTP 路由
├── practice/               # 学习阶段的脚本归档，保留演进轨迹
│   ├── phase0/             # 连通性验证
│   ├── phase1/             # 单表 CRUD
│   ├── phase2/             # 建表进阶
│   ├── phase3/             # 多表查询与 JOIN
│   ├── phase4/             # 事务与并发控制
│   ├── phase5/             # 索引与性能优化
│   ├── phase6/             # 数据库设计
│   └── legacy/             # 最早的 PyMySQL 用户管理系统（教程第二章的改造对象）
├── sql/                    # 独立 SQL 脚本
├── notes/                  # 学习笔记
├── tests/                  # 自动化测试
├── .env.example
└── requirements.txt
```

## 快速开始

```bash
# 1. 虚拟环境与依赖
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash
pip install -r requirements.txt

# 2. 配置（.env 已被 .gitignore 忽略）
cp .env.example .env                 # 填入真实密码

# 3. 启动
uvicorn app.main:app --reload
```

接口文档：http://127.0.0.1:8000/docs

健康检查：

```bash
curl http://127.0.0.1:8000/health      # 进程存活
curl http://127.0.0.1:8000/health/db   # 数据库连通 + 版本
```

## 分层约定

| 层 | 只负责 | 禁止 |
| --- | --- | --- |
| `routers/` | HTTP 入参出参、状态码、依赖注入 | 写 SQL、写业务规则 |
| `services/` | 业务规则、事务提交与回滚 | 感知 HTTP、返回 Response |
| `models/` | 表结构映射、关系定义 | 业务判断 |
| `db/` | Engine / Session 生命周期 | 业务代码 |
| `core/` | 配置、安全、异常定义 | 依赖上层模块 |

调用方向单向：`routers → services → models`，反向依赖一律视为设计错误。

## 学习进度

| 阶段 | 主题 | 笔记 | 代码 |
| --- | --- | --- | --- |
| 0 | 环境搭建与连通 | [阶段0](notes/阶段0%20--%20环境搭建与连通.md) | `practice/phase0/` |
| 1 | 单表 CRUD 与基础查询 | [阶段1](notes/阶段1%20--%20单表%20CRUD%20与基础查询.md) | `practice/phase1/` |
| 2 | 建表进阶 | [阶段2](notes/阶段2%20--%20建表进阶.md) | `practice/phase2/` |
| 3 | 多表查询与 JOIN | [阶段3](notes/阶段3%20--%20多表查询与%20JOIN.md) | `practice/phase3/` |
| 4 | 事务与并发控制 | [阶段4](notes/阶段%204：事务与并发控制.md) | `practice/phase4/` |
| 5 | 索引与性能优化 | [阶段5](notes/阶段5%20--%20索引与性能优化.md) | `practice/phase5/` |
| 6 | 数据库设计（范式与建模） | [阶段6](notes/阶段6%20--%20数据库设计（范式与建模）.md) | `practice/phase6/` |
| 7 | 运维与架构 | [阶段7](notes/阶段7%20--%20运维与架构.md) | — |

进阶实战路线见 [Python + MySQL 进阶实战教程](notes/Python%20+%20MySQL%20进阶实战教程.md)。

## 安全说明

- 所有数据库凭据一律通过环境变量 / `.env` 传入，仓库内**不含任何密码**。
- `.env`、`.venv/`、`__pycache__/` 均在 `.gitignore` 中。
