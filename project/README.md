# 用户管理系统 API

基于 **FastAPI + SQLAlchemy 2.0 + MySQL 8.0** 的用户管理后端,提供注册登录、用户增删改查、角色权限控制与转账事务。

## 功能

- **认证**：注册、登录、JWT 令牌签发与校验
- **密码安全**：argon2 哈希存储,明文不落库
- **用户管理**：列表（分页）、详情、创建、改余额、软删除
- **角色权限**：用户与角色多对多,接口按角色鉴权（401 / 403 区分）
- **事务**：转账在同一事务内扣加,任一步失败整体回滚
- **测试**：8 个接口用例,覆盖认证与权限分支

## 技术栈

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.12 | 运行环境 |
| MySQL | 8.0 | 数据库 |
| FastAPI | 0.162 | Web 框架 |
| uvicorn | 0.54 | ASGI 服务器 |
| SQLAlchemy | 2.1 | ORM 与连接池 |
| Alembic | 1.20 | 数据库迁移 |
| Pydantic v2 | 2.14 | 请求响应模型与校验 |
| PyMySQL | 1.2 | MySQL 驱动 |
| argon2-cffi | 25.1 | 密码哈希 |
| PyJWT | 2.15 | JWT 签发与校验 |
| pytest | 9.2 | 自动化测试 |

## 目录结构

```plain
project/
├── app/
│   ├── main.py               # 应用入口：路由注册、异常处理、生命周期
│   ├── deps.py               # 依赖：get_db、get_current_user、require_role
│   ├── core/
│   │   ├── config.py         # 配置（读 .env）
│   │   ├── security.py       # 密码哈希与 JWT
│   │   └── exceptions.py     # 业务异常,自带状态码
│   ├── db/
│   │   ├── base.py           # DeclarativeBase
│   │   ├── engine.py         # Engine + 连接池
│   │   └── session.py        # SessionLocal 与 get_db
│   ├── models/               # User / Order / Role
│   ├── schemas/              # 请求响应模型
│   ├── services/             # 业务逻辑与事务边界
│   └── routers/              # health / auth / users / wallet
├── migrations/               # Alembic 迁移（0001 ~ 0003）
├── tests/                    # pytest 用例
├── alembic.ini
├── requirements.txt
└── .env.example
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/Scripts/activate          # Windows CMD/PowerShell 用 .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env,填入真实的数据库密码
```

可用配置项：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MYSQL_HOST` | `localhost` | 数据库地址 |
| `MYSQL_PORT` | `3306` | 端口 |
| `MYSQL_USER` | `root` | 用户名 |
| `MYSQL_PASSWORD` | 空 | 密码 |
| `MYSQL_DATABASE` | `learn_mysql` | 数据库名 |
| `DB_POOL_SIZE` | `5` | 连接池常驻连接数 |
| `DB_MAX_OVERFLOW` | `10` | 高峰允许超出的连接数 |
| `DB_POOL_RECYCLE` | `3600` | 连接存活秒数,到时重建 |
| `DB_ECHO` | `false` | 是否打印 SQL |
| `JWT_SECRET` | dev 默认值 | 签名密钥,**生产必须替换**,长度 ≥ 32 字节 |
| `JWT_EXPIRE_MINUTES` | `60` | 令牌有效期 |

### 3. 建库与迁移

```bash
alembic upgrade head
alembic current        # 0003_password (head)
```

### 4. 启动

```bash
uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000/docs 查看自动生成的接口文档。

## 接口清单

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/health` | 公开 | 进程存活探测 |
| GET | `/health/db` | 公开 | 数据库连通探测 |
| POST | `/auth/register` | 公开 | 注册,返回用户信息 |
| POST | `/auth/login` | 公开 | 登录,返回 JWT |
| GET | `/auth/me` | 登录 | 当前用户信息与角色 |
| GET | `/users` | 公开 | 分页列表（自动过滤软删） |
| GET | `/users/{id}` | 公开 | 用户详情 |
| POST | `/users` | 公开 | 创建用户（管理用途） |
| PUT | `/users/{id}/balance` | 公开 | 调整余额 |
| DELETE | `/users/{id}` | 公开 | 软删除 |
| GET | `/users/{id}/roles` | 公开 | 查询角色 |
| POST | `/users/{id}/roles` | **admin** | 分配角色 |
| POST | `/transfer` | 登录 | 转账 |

### 认证流程

```bash
# 1. 注册
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","phone":"13800000000","password":"secret123"}'

# 2. 登录,拿到令牌
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"secret123"}'
# → {"access_token":"eyJ...","token_type":"bearer","expires_in":3600}

# 3. 带令牌访问受保护接口
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <粘贴上一步的 access_token>"
```

## 数据模型

| 表 | 说明 |
| --- | --- |
| `users` | 用户：用户名、手机号、余额、密码哈希、软删标记 |
| `orders` | 订单：演示一对多关系（`user_id` 逻辑外键） |
| `roles` | 角色：admin / editor / viewer |
| `user_roles` | 用户-角色关联表,联合主键防重复 |

## 测试

```bash
python -m pytest tests -v
```

```plain
tests/test_auth.py::test_register_success PASSED
tests/test_auth.py::test_register_duplicate PASSED
tests/test_auth.py::test_register_weak_password PASSED
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_wrong_password PASSED
tests/test_auth.py::test_me_without_token PASSED
tests/test_auth.py::test_me_with_token PASSED
tests/test_auth.py::test_assign_role_forbidden PASSED

8 passed
```

测试直接连开发库,用例通过 `temp_user` fixture 自建自清,不会污染数据。

## 设计说明

**分层**：`routers → services → models`,单向依赖。

| 层 | 负责 | 不负责 |
| --- | --- | --- |
| `routers/` | HTTP 入参出参、状态码、依赖注入 | 写 SQL、写业务规则 |
| `services/` | 业务规则、事务边界、抛业务异常 | 感知 HTTP |
| `models/` | 表结构映射与关系 | 业务判断 |

**异常映射**：service 抛 `AppError` 子类,`main.py` 统一转成 HTTP 响应。

| 异常 | 状态码 |
| --- | --- |
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `UnauthorizedError` | 401 |
| `ForbiddenError` | 403 |
| `AppError` | 400 |

**软删除**：`users.is_deleted` 置 1,行保留；列表查询统一在 service 层过滤。

**事务**：转账只 `commit()` 一次,异常时 `rollback()`,保证两边余额一致。

**迁移**：所有表结构变更走 Alembic,不使用 `create_all`；`env.py` 中的 `include_object` 会忽略库中未建模的表,防止误生成 `DROP TABLE`。

## 已知限制

- 转账使用"读出来改属性"的写法,并发下存在丢更新风险,生产环境应改用 `with_for_update()` 或原子 SQL。
- 测试直接连开发库,未使用独立测试库。
- JWT 无状态,暂不支持主动失效（如改密码后踢下线）。
