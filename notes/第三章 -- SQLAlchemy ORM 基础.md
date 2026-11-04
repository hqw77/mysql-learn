# 第三章 -- SQLAlchemy ORM 基础

> 对应教程第三章。产物：`app/models/user.py`、`migrations/`（Alembic 基线）
> 上一章：连接池（`app/db/engine.py` 里的 `pool_size` 就是那个知识点的工程化）

## 1. 学习目标

- 说清 ORM 与原生 SQL 的边界：什么时候该用，什么时候不该用
- 认识 SQLAlchemy 的六个核心对象：Engine / Dialect / Pool / Connection / Session / Model
- 会用 2.0 风格定义模型：`DeclarativeBase` + `Mapped[T]` + `mapped_column()`
- 能把 MySQL 的列类型准确映射成 SQLAlchemy 类型（含 `unsigned`、`DECIMAL`）
- 理解 `server_default` 与 `default` 的区别
- 会用 Alembic 接管建表，而不是 `create_all`

## 2. 什么是 ORM

ORM（Object Relational Mapping）把「表」映射成「类」、把「行」映射成「对象」：

```plain
数据库视角                        Python 视角
─────────────────────────────────────────────────────────
TABLE users                    class User(Base)
  ├─ id      INT UNSIGNED  ←→    id: Mapped[int]
  ├─ username VARCHAR(50)  ←→    username: Mapped[str]
  └─ balance  DECIMAL(10,2)←→    balance: Mapped[Decimal]

SELECT * FROM users WHERE id=1 ←→  db.get(User, 1)
UPDATE users SET balance=100   ←→  user.balance = 100; db.commit()
```

### ORM 与原生 SQL 的取舍

| 场景 | 推荐 | 原因 |
| --- | --- | --- |
| 常规 CRUD、单表/简单关联 | ORM | 写得快，字段改名有 IDE 提示 |
| 复杂报表、多表聚合、窗口函数 | 原生 SQL | ORM 生成的 SQL 往往不如手写清晰 |
| 批量导入百万行 | 原生 SQL / `execute` 批量 | ORM 逐个实例化开销大 |
| 需要精确控制执行计划 | 原生 SQL | 能直接看 `EXPLAIN` 出来的语句 |

结论：**ORM 不是替代 SQL，是替代重复的样板 SQL**。`practice/` 里那套 PyMySQL 写法在 `app/` 里不会消失，只是被封装进 `db/` 和 `models/`。

## 3. SQLAlchemy 架构

```plain
  你的代码
     │
     ▼
┌──────────────┐   声明式模型（Model）
│  models/     │ ──────────────► MetaData（表结构的内存描述）
└──────┬───────┘
       │ Session（工作单元：跟踪对象变化、管事务）
       ▼
┌──────────────┐
│  Session     │
└──────┬───────┘
       │ Connection（一次数据库会话）
       ▼
┌──────────────┐
│  Engine      │ ◄── 持有连接池（QueuePool）
└──────┬───────┘
       │ Dialect（把 SQLAlchemy 表达式编译成 MySQL 方言）
       ▼
   PyMySQL 驱动
       ▼
    MySQL 8.0
```

对照本仓库：

| 对象 | 文件 |
| --- | --- |
| Engine | `app/db/engine.py` |
| Session | `app/db/session.py` |
| MetaData / Model | `app/db/base.py` + `app/models/user.py` |
| Dialect + 驱动 | 连接串里的 `mysql+pymysql` |
| 连接池 | Engine 内置 `QueuePool` |

**Engine 和 Session 的区别**（面试必问）：Engine 是进程级的、长生命周期的，管连接池；Session 是请求级的、短生命周期的，管一次业务操作的对象状态和事务。一个 Engine 可以派生无数 Session。

## 4. 连接字符串

格式：

```plain
dialect+driver://user:password@host:port/database?charset=utf8mb4
```

本项目的实现（`app/core/config.py`）：

```python
f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{database}?charset=utf8mb4"
```

两个细节：

1. **密码必须 `quote_plus`**。密码里如果有 `@`、`:`、`/`、`#`，不编码会把连接串截断，报错信息还很难懂。
2. `mysql+pymysql` 表示「MySQL 方言 + PyMySQL 驱动」。换成 `mysql+mysqldb` 就是另一个驱动，SQL 不用改。

## 5. 定义模型（2.0 风格）

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
```

关键点：

- `Mapped[T]` 是**类型声明**，给 IDE 和类型检查器看；`mapped_column()` 是**列声明**，给数据库看
- 两者结合，`user.username` 会被推断为 `str`，`user.balance` 为 `Decimal`
- 1.x 的写法是 `id = Column(Integer, primary_key=True)`，没有类型信息，现在不推荐

### 类型映射对照

| Python 类型 | SQLAlchemy 类型 | MySQL 实际类型 | 说明 |
| --- | --- | --- | --- |
| `int` | `INTEGER(unsigned=True)` | `INT UNSIGNED` | `unsigned` 只有 MySQL 方言有，要从 `sqlalchemy.dialects.mysql` 导入 |
| `str` | `String(50)` | `VARCHAR(50)` | 必须给长度，MySQL 建表需要 |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` | 金额一律用它，绝不用 `Float` |
| `bool` | `TINYINT(1)` | `TINYINT(1)` | 与库里 `is_deleted` 一致 |
| `datetime` | `DateTime` | `DATETIME` | 时区无关，存什么读什么 |

### `server_default` 与 `default`

```python
balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0.00"))
```

- `server_default` → 写进 **DDL** 的 `DEFAULT`，由 MySQL 填充，`SHOW CREATE TABLE` 能看到
- `default` → 由 **Python 端**在 INSERT 时填充，DDL 里没有

要保证「模型和库结构一致」，就得用 `server_default`。用 `default` 的话，`alembic check` 会一直报差异。

## 6. Session 的用法

```python
from app.db.session import SessionLocal
from app.models import User
from sqlalchemy import select

with SessionLocal() as db:
    users = db.scalars(select(User)).all()     # 查询
    user = db.get(User, 1)                     # 按主键取
```

`SessionLocal` 是 `sessionmaker`，`with` 块结束会 `close()` —— 这里的 `close()` 是**把连接还给池**，不是断开，正是第二章的结论。

FastAPI 里不直接 `with`，而是用依赖：

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`yield` 保证请求异常时也会归还连接。

## 7. 建表：`create_all` 还是 Alembic

教程用的是 `Base.metadata.create_all(engine)`。它能用，但这本仓库**不能用**，原因很实在：

库里已经有 11 张表和真实数据（`students` 4 行、`orders` 3 行、`big_users` 99,822 行）。

- `create_all` 只会创建**缺失**的表，已有的表不检查、不修改
- 想加一列？`create_all` 什么都不做
- 想改名？更不会

所以从第三章起直接上 Alembic。这也符合真实项目：**表结构变更要可追溯、可回滚**。

### Alembic 的三个概念

| 概念 | 含义 |
| --- | --- |
| `revision` | 一个迁移版本，一个 Python 文件 |
| `upgrade()` / `downgrade()` | 前进 / 回退的具体 DDL |
| `alembic_version` 表 | 记录当前库处在哪个 revision |

## 8. 实战：给现有库建基线

表已经在库里，所以不能直接 `alembic upgrade head`（会撞 `Table already exists`）。正确做法是「先写迁移，再 stamp」：

```bash
# 1. 初始化（只做一次）
alembic init migrations

# 2. 手写第一个 revision，内容 = 现有 users 表的 DDL
#    migrations/versions/0001_initial_schema.py

# 3. 标记为"已执行"，但不真的执行
alembic stamp head

# 4. 确认
alembic current          # 0001_initial (head)
alembic check            # No new upgrade operations detected.
```

`alembic_version` 表实际写入：

```plain
version_num
-----------
0001_initial
```

之后加新列就是：

```bash
alembic revision --autogenerate -m "add password_hash to users"
alembic upgrade head
```

## 9. 一个容易踩的坑：autogenerate 会删表

第一次跑 `alembic check` 时，它报了这么一堆：

```plain
Detected removed table 'orders'
Detected removed table 'authors'
Detected removed table 'big_users'
...
```

原因：`learn_mysql` 里还有第一章留下的练习表（`students`/`books`/`orders`…），它们**没有对应的 ORM 模型**。autogenerate 的逻辑是「模型里没有、库里有 → 判定为要删除」。

如果这时候手一抖执行了 `alembic revision --autogenerate`，生成的迁移里就是**一串 DROP TABLE**，`upgrade` 一下数据全没。

解决办法是在 `migrations/env.py` 里加过滤：

```python
def include_object(object_, name, type_, reflected, compare_to):
    # 库里存在但模型没定义的对象，一律不管
    if reflected and compare_to is None:
        return False
    return True
```

然后传给 `context.configure(..., include_object=include_object)`。

**这条规则的含义要记住**：本项目里，Alembic 只负责「模型里写过的表」，练习表不归它管。

## 10. 验证

```bash
# 1. 模型能注册
python -c "from app.models import User; from app.db.base import Base; print(Base.metadata.tables.keys())"

# 2. ORM 能查出真实数据
python -c "
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import User
with SessionLocal() as db:
    for u in db.scalars(select(User)).all():
        print(u)
"
```

实测输出：

```plain
<User id=1 username='张三' balance=888.00>
<User id=2 username='李四' balance=400.00>
<User id=3 username='王五' balance=100.00>
```

```bash
# 3. 模型与库结构一致
alembic check     # No new upgrade operations detected.
```

## 11. 常见错误排查

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| `UnicodeDecodeError: 'gbk' codec can't decode` | `alembic.ini` 里有中文，Alembic 用系统 locale 读配置 | 把 ini 里的注释改成纯 ASCII |
| `Table 'xxx' already exists` | 表已存在还执行了初始迁移 | 用 `alembic stamp head` 而不是 `upgrade` |
| autogenerate 生成一堆 `DROP TABLE` | 库里有未建模的表 | 加 `include_object` 过滤 |
| `alembic check` 一直报 comment 差异 | 模型的 `comment` 和库里不一致 | 对齐即可，或删掉模型里的 comment |
| `ArgumentError: Could not parse SQLAlchemy URL` | 密码含特殊字符没编码 | `quote_plus(password)` |
| `RuntimeError: 'cryptography' package is required` | MySQL 8 默认 `caching_sha2_password` | `pip install cryptography` |

## 12. 高频面试题

1. **什么是 ORM？优缺点？**
   对象关系映射。优点：开发快、防注入、字段有类型、换库成本低；缺点：复杂查询表达力弱、隐藏了 SQL 开销、批量操作性能差。

2. **Engine 和 Session 的区别？**
   Engine 是进程级连接池持有者，长生命周期、线程安全；Session 是请求级工作单元，管对象身份映射（identity map）、脏检查、事务边界，不线程安全。

3. **Session 和数据库连接是什么关系？**
   Session 在执行 SQL 时才从 Engine 的连接池借连接，用完归还。Session 本身不持有固定连接。

4. **`create_all` 和迁移工具的区别？**
   `create_all` 只建缺失的表，不改已有结构、不记录版本、无法回滚；迁移工具（Alembic）把每次变更固化成版本文件，可逐步升级、可回退、可审计。

5. **`server_default` 和 `default` 的区别？**
   `server_default` 写在 DDL 里由数据库执行；`default` 由 Python 在 INSERT 前填充。要保证 DDL 与模型一致必须用前者。

## 13. 本章总结

- ORM 替代的是样板 SQL，不是复杂 SQL
- 2.0 风格：`Mapped[T]` 管类型，`mapped_column()` 管列
- 类型映射要精确到 `unsigned`、`DECIMAL`，否则 `alembic check` 永远不干净
- Engine 管池，Session 管事务，两者生命周期不同
- 已有数据的库不要用 `create_all`，用 Alembic 基线 + `stamp`
- **autogenerate 前必须加 `include_object`**，否则会把你没建模的表判成待删除

下一章：用 Session 做完整 CRUD，并把逻辑挪进 `app/services/`。
