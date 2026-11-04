# 第三章 · SQLAlchemy ORM 基础

> **一句话总结**：ORM 就是把「发 SQL、拿字典、自己拼字符串」换成「拿对象、改属性、提交」。

**本章只解决四个问题**，别的一概不碰：

| # | 问题 | 产出 |
| --- | --- | --- |
| 1 | Engine 是什么 | 一行 `create_engine` |
| 2 | Base 是什么 | 三行 `class Base(DeclarativeBase)` |
| 3 | Model 怎么用 2.0 语法写 | 一个 `User` 类 |
| 4 | 怎么用 Session 查出一条数据 | `session.get(User, 1)` |

> ⏭️ **建表迁移（Alembic）不在本章**，已抽到 [番外01 -- Alembic 数据库迁移](番外01%20--%20Alembic%20数据库迁移.md)。本章假设表已经存在——你库里的 `users` 表早就有了。

---

## 0. 一页纸看懂本章

```plain
你的代码
   │  user = session.get(User, 1)
   ▼
┌────────────┐
│  Session   │  工作单元：记着"哪些对象被改过"，管一次事务
└─────┬──────┘
      │ 需要用连接时，才向 Engine 借
      ▼
┌────────────┐
│   Engine   │  进程级唯一，内部持有一个连接池
└─────┬──────┘
      │
      ▼
   PyMySQL  →  MySQL 8.0
```

四个角色的分工，一句话一个：

- **Engine**：连接池的持有者，全进程建一个
- **Base**：模型登记册，所有 Model 挂在它下面
- **Model**：一个类 = 一张表，一个属性 = 一列
- **Session**：一次业务操作的工作单元，管事务和对象状态

---

## 1. Step 1 · 30 行跑通第一条查询

先别管什么分层、目录、配置。就一个文件，跑通再说。

```python
# mini_orm.py —— 先跑通，再谈架构
import os
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, create_engine
from sqlalchemy.dialects.mysql import INTEGER, TINYINT  # ⚠️ 别用通用的 sqlalchemy.INTEGER，它不认 unsigned
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# ① Engine：进程级唯一，内部自带连接池
engine = create_engine(
    f"mysql+pymysql://root:{os.getenv('MYSQL_PASSWORD', '')}"
    f"@localhost:3306/learn_mysql?charset=utf8mb4",
    # 💡 学习期把 echo 打开，每条生成的 SQL 都会打出来，比看文档快十倍
    echo=True,
)


# ② Base：所有模型的基类
class Base(DeclarativeBase):
    pass


# ③ Model：一个类 = 一张表
class User(Base):
    __tablename__ = "users"

    # 💡 Mapped[int] 是给 IDE 和类型检查器看的，mapped_column 是给数据库看的
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_deleted: Mapped[bool] = mapped_column(TINYINT(1))
    created_at: Mapped[datetime] = mapped_column(DateTime)


# ④ Session：一次业务操作的工作单元
with Session(engine) as session:
    user = session.get(User, 1)          # 主键查一条
    print(user.username, user.balance)
```

运行结果：

```plain
张三 888.00
```

同时控制台会打出它替你生成的 SQL：

```sql
SELECT users.id, users.username, users.phone, users.balance,
       users.is_deleted, users.created_at
FROM users
WHERE users.id = %(pk_1)s
```

### 核心知识点提炼

| 你以为在做 | 实际发生了什么 |
| --- | --- |
| `session.get(User, 1)` | 生成 `SELECT ... WHERE id = 1`，查出 1 行 |
| 返回值是 `User` 对象 | 一行数据被"翻译"成对象，列名变成属性名 |
| `user.balance` | 直接返回 `Decimal('888.00')`，不需要 `row["balance"]` |
| `with Session(...)` 结束 | 自动 `close()`，连接归还连接池（**不是断开**） |

> ⚠️ `print(user)` 会打出一串 `<__main__.User object at 0x...>`，这不是 bug。想要好看的输出，加个 `__repr__`，第 3 节会写。

---

## 2. 拆开这 30 行

### 2.1 Engine —— 连接池的持有者

```python
engine = create_engine(url, echo=True)
```

就这一个对象，全进程建一次就够了。它内部维护连接池，`pool_pre_ping=True` 能防止用到被 MySQL 掐断的死连接——这就是第二章那个知识点的落地方式，参数含义一句话带过即可。

```python
# 💡 生产配置就多两行，其余默认值够用
engine = create_engine(
    url,
    pool_pre_ping=True,   # 借出前探活，解决 MySQL 8 小时断连
    pool_recycle=3600,    # 连接活过 1 小时就换新的
)
```

> ⚠️ **绝对不要在每个请求里 `create_engine`**。它是重对象，创建一次要初始化整个连接池。写进函数体是新手最常见的性能事故。

### 2.2 Base —— 模型登记册

```python
class Base(DeclarativeBase):
    pass
```

看着是个空类，其实它持有 `Base.metadata`——一张「本进程注册了哪些表」的登记表。每个继承它的 Model 都会自动登记上去。

> ⚠️ **模型必须被 import 过才会注册**。如果你写了 `app/models/order.py` 但没有任何地方 import 它，`Base.metadata` 里就没有它，之后建表/迁移都会漏掉这张表。报错长这样：`sqlalchemy.exc.NoReferencedTableError` 或迁移里少了表。
>
> 约定：在 `app/models/__init__.py` 里把每个模型都 export 一次，就是为了防这个。

### 2.3 Model —— 类与表的映射

```python
class User(Base):
    __tablename__ = "users"                                  # 表名
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
```

两个东西必须成对出现：

- `Mapped[int]` → **Python 侧**的类型声明，决定 `user.id` 是 `int`
- `mapped_column(...)` → **数据库侧**的列定义，决定建表时是 `INT UNSIGNED`

#### 类型怎么对应

| Python | SQLAlchemy | MySQL | 注意 |
| --- | --- | --- | --- |
| `int` | `INTEGER(unsigned=True)` | `INT UNSIGNED` | `unsigned` 只有 MySQL 方言有 |
| `str` | `String(50)` | `VARCHAR(50)` | 必须给长度 |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` | 金额只用它，永远不用 `Float` |
| `bool` | `TINYINT(1)` | `TINYINT(1)` | 对应库里的 `is_deleted` |
| `datetime` | `DateTime` | `DATETIME` | 不带时区，存什么读什么 |

> ⚠️ `unsigned=True` 必须从 `sqlalchemy.dialects.mysql` 导入 `INTEGER`，通用的 `sqlalchemy.INTEGER` 不认这个参数，会直接 `TypeError`。

#### `default` 和 `server_default` 的区别（实测建表 SQL）

很多教程一句话带过，但这两个东西生成的 DDL 完全不同：

```python
Column("balance", Numeric(10, 2), nullable=False, server_default=text("0.00"))
Column("balance", Numeric(10, 2), nullable=False, default=Decimal("0.00"))
```

实际编译出来的建表语句：

```sql
-- server_default
CREATE TABLE t_server (
    balance NUMERIC(10, 2) NOT NULL DEFAULT (0.00)     -- ✅ DDL 里有 DEFAULT
)

-- default
CREATE TABLE t_python (
    balance NUMERIC(10, 2) NOT NULL                     -- ❌ DDL 里什么都没有
)
```

| | `server_default` | `default` |
| --- | --- | --- |
| DEFAULT 写进建表语句 | 是 | 否 |
| 谁来填值 | MySQL | Python（INSERT 前） |
| 绕过 ORM 直接 INSERT 时 | 也会生效 | **不生效**，列会报错/为空 |
| 什么时候用 | 想让库结构自带默认值 | 只在 Python 层兜底 |

**结论**：想和数据库结构保持一致，用 `server_default`。`default` 只是 Python 侧的保险，别指望它出现在表结构里。

### 2.4 Session —— 工作单元

```python
with Session(engine) as session:
    user = session.get(User, 1)
```

Session 干的活比"执行 SQL"多得多：

- 管**事务边界**（commit / rollback）
- 管**身份映射**（同一个 id 查两次，返回同一个对象）
- 管**脏检查**（记着哪些对象的属性被改过）

> ⚠️ **Session 不是线程安全的**。一个线程一个 Session，或者一个请求一个 Session。共享 Session 会出现难以复现的数据错乱。

---

## 3. 同一件事，两种写法

### 3.1 以前用 PyMySQL

```python
import pymysql
from pymysql.cursors import DictCursor

conn = pymysql.connect(host="localhost", user="root", password=..., database="learn_mysql")
with conn.cursor(DictCursor) as cur:
    cur.execute("SELECT * FROM users WHERE id = %s", (1,))
    row = cur.fetchone()

print(row["username"])
```

拿到的是一行字典（实测）：

```plain
{'id': 1, 'username': '张三', 'phone': '13800000001',
 'balance': Decimal('888.00'), 'is_deleted': 0,
 'created_at': datetime.datetime(2026, 11, 3, 16, 7, 59)}
```

### 3.2 现在用 ORM

```python
with Session(engine) as session:
    user = session.get(User, 1)
    print(user.username)
```

### 3.3 差别在哪

| 维度 | PyMySQL | SQLAlchemy ORM |
| --- | --- | --- |
| 你写的东西 | SQL 字符串 | 方法调用 |
| 拿到的东西 | `dict` | `User` 对象 |
| 取字段 | `row["username"]` | `user.username`（IDE 有补全） |
| 改数据 | 自己拼 `UPDATE` | `user.balance = 100` |
| 类型检查 | 运行时才知道 | 写代码时就知道 |
| 复杂联表 | 写得爽 | 要绕一下 |

> 💡 ORM 替代的是**重复的样板 SQL**，不是复杂查询。报表、多表聚合、批量导入，照样手写 SQL。

---

## 4. Step 2 · 脏检查：ORM 最反直觉的机制

这是新手到进阶之间真正的分水岭。

### 4.1 先看现象

```python
with Session(engine) as session:
    user = session.get(User, 1)
    print(user.balance)        # 888.00

    user.balance = Decimal("9999.00")
    print(session.dirty)       # 它已经知道这个对象被改过了
```

实测输出：

```plain
改之前 balance = 888.00
session.dirty = IdentitySet([<User ...>])     # 对象进入了"脏集合"
内存里的值 = 9999.00
```

### 4.2 那什么时候才真的发 UPDATE？

答案：**flush 的时候**（`commit()` 会自动触发一次 flush）。

我用 `echo=True` 抓了真实 SQL，做了两组对照：

```plain
>>> A. 赋一个相同的值
SELECT users.id, users.username, ... FROM users WHERE users.id = 1
（没有 UPDATE！）

>>> B. 赋一个不同的值
SELECT users.id, users.username, ... FROM users WHERE users.id = 1
UPDATE users SET balance=%(balance)s WHERE users.id = 1
```

两个结论，都很反直觉：

1. **赋相同的值，虽然对象进了 dirty 集合，但 flush 时不发 UPDATE**。SQLAlchemy 在 flush 时会比较属性快照，值没变就不写库。
2. **UPDATE 只带你改过的那一列**，不是整行覆盖。所以不会有"并发覆盖别人字段"的问题——但同一列的并发冲突依然存在。

### 4.3 完整链路

```plain
user.balance = 100
      │
      ▼
① 标记为脏（dirty）        ← 此刻什么都没发给数据库
      │
      ▼
② session.commit() / flush()
      │
      ▼
③ 对比内存值与加载时的快照
      │
      ├── 没变 → 跳过，不发 SQL
      └── 变了 → UPDATE 只带变化的列
      │
      ▼
④ COMMIT 写盘
```

### 4.4 回滚

```python
user.balance = Decimal("9999.00")
session.rollback()
print(session.get(User, 1).balance)   # 888.00，回到原值
```

`rollback()` 不只是回滚数据库，还会把内存里对象的修改**一并丢弃**。

### 核心知识点提炼

| 概念 | 一句话 |
| --- | --- |
| 脏检查（dirty checking） | 改属性时只打标记，不发 SQL |
| flush | 把内存变更同步到数据库（事务内，还没提交） |
| commit | flush + 提交事务 |
| 身份映射 | 同一 Session 内同 id 只查一次，返回同一对象 |
| 快照对比 | 值没变就不发 UPDATE，省掉无意义的写 |

> ⚠️ **别在循环里无脑 `commit()`**。每次 commit 都是一次 flush + 一次网络往返。批量写 1000 行，正确做法是 `add_all` 后 commit 一次。

---

## 5. Step 3 · 从 30 行到 `app/`：为什么要拆

跑通之后再看仓库里的结构，就不会觉得是"为了规范而规范"了。

### 5.1 一个文件的问题

`mini_orm.py` 能跑，但它有三个硬伤：

| 问题 | 后果 |
| --- | --- |
| 连接串硬编码在文件里 | 换环境就要改代码，密码进了 git |
| `engine` 和 `Base` 定义在模块顶层 | 其他文件想用只能 import 这个脚本，会连带执行查询 |
| 没有地方放"第 2 个模型" | 加 `Order` 就开始复制粘贴 |

### 5.2 拆成什么样

| mini 版 | app/ 版 | 为什么 |
| --- | --- | --- |
| 那一行 `create_engine(...)` | `app/db/engine.py` | 连接池全进程唯一，集中管理 |
| `class Base(DeclarativeBase)` | `app/db/base.py` | 所有模型共用，迁移工具也要它 |
| `class User(Base)` | `app/models/user.py` | 一个文件一个模型，好找 |
| `Session(engine)` | `app/db/session.py` 的 `SessionLocal` | 工厂函数，按请求创建 |
| 连接串 | `app/core/config.py` + `.env` | 配置与代码分离 |
| `with Session(...)` | `app/deps.py` 的 `get_db` | 注入给路由，用 `yield` 保证释放 |

### 5.3 拆完之后，用起来是这样的

```python
from app.db.session import SessionLocal
from app.models import User

with SessionLocal() as db:
    user = db.get(User, 1)
```

从 30 行变成 5 个文件，但**调用方式几乎没变**——这就是好的抽象：复杂度被关进了 `db/` 和 `core/`，业务代码只看见 `db.get(User, 1)`。

> ⚠️ 拆分的收益在"第 2 个、第 3 个模型"出现时才显现。只有一张表的时候，拆不拆都行。别为了架构而架构，但也别等到 10 张表才开始拆。

---

## 6. 业务场景对话

**Q：查一条数据，用 `session.get()` 还是 `session.execute(select(...))`？**

`get()` 只接受主键，好处是**先查身份映射**——如果这个对象已经在 Session 里，直接返回，不查库。所以"按 id 取"永远优先 `get()`。

按非主键条件查（比如按用户名），只能用 `select()`：

```python
from sqlalchemy import select

user = session.execute(
    select(User).where(User.username == "张三")
).scalar_one_or_none()
```

> 💡 `scalar_one_or_none()` 比 `scalar_one()` 安全：查不到返回 `None`，而不是抛异常。

**Q：为什么公司里禁止在 `for` 循环里 `session.get()`？**

因为这会造成 **N+1 查询**：循环 100 次就是 100 次数据库往返。正确做法是一次性捞回来：

```python
# ⚠️ 别这样
for uid in user_ids:
    print(session.get(User, uid).username)

# 💡 一次查完
users = session.scalars(select(User).where(User.id.in_(user_ids))).all()
```

**Q：查不到数据，`get()` 返回什么？**

返回 `None`，**不抛异常**。所以业务里判断"用户不存在"就是 `if user is None`，不用 try/except。

---

## 7. 常见报错排查

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:mysql.pymysql` | 没装 PyMySQL，或连接串写错 | `pip install PyMySQL`，串是 `mysql+pymysql://` |
| `Table 'xxx.users' doesn't exist` | 连错库 | 检查连接串里的 database |
| `Access denied for user 'root'@'localhost'` | 密码错 | 检查 `MYSQL_PASSWORD` |
| `ArgumentError: Could not parse SQLAlchemy URL` | 密码含 `@ : / #` 没编码 | `quote_plus(password)` |
| `MappedAnnotationError` / `Could not determine join condition` | `Mapped[...]` 写错或关系没配 | 检查类型标注，关系问题下一章讲 |
| `TypeError: 'unsigned' is an invalid keyword argument` | 用了通用 `INTEGER` | 从 `sqlalchemy.dialects.mysql` 导入 |
| 时间差 8 小时 | `DATETIME` 无时区，Python `datetime.now()` 带本地时区混用 | 统一用库里的 `server_default`，别自己塞时间 |
| `DetachedInstanceError` | Session 关闭后又访问对象属性 | 在 `with` 块内取完需要的字段，或调 `expire_on_commit=False` |

---

## 8. FAQ：3 个高频面试题

### Q1. Engine 和 Session 的区别是什么？

> **满分回答模板：**
>
> 一句话：**Engine 管连接，Session 管事务和对象**。
>
> 展开三点：
> 1. **生命周期不同**——Engine 是进程级的，应用启动建一次，跟着进程走；Session 是请求级或操作级的，用完就关。
> 2. **职责不同**——Engine 内部持有连接池，负责"怎么连数据库"；Session 是工作单元，负责"这次业务做了哪些操作、要不要提交"。
> 3. **线程安全性不同**——Engine 线程安全，可以共享；Session 不是，必须一个线程/请求一个。
>
> 补充一句加分项：Session 并不会一直占着连接，它只在执行 SQL 时才向 Engine 借，用完立刻还。

### Q2. ORM 的"脏检查"是怎么工作的？什么时候发 UPDATE？

> **满分回答模板：**
>
> 一句话：**改属性只打标记，flush 时才对比快照决定发不发 SQL**。
>
> 展开：
> 1. 对象从库里查出来时，SQLAlchemy 会保留一份属性快照。
> 2. 你执行 `user.balance = 100`，对象进入 Session 的 dirty 集合，但**此刻没有任何 SQL 发出**。
> 3. 调用 `commit()` / `flush()` 时，逐字段对比当前值和快照。没变就跳过；变了就生成 `UPDATE`，且**只带变化的列**。
>
> 加分项：因为只更新变化列，多个人同时改同一行的不同字段不会互相覆盖；但同一字段的并发冲突仍然要靠乐观锁或 `SELECT ... FOR UPDATE` 解决，这是 ORM 管不了的。

### Q3. 什么时候该用 ORM，什么时候该写原生 SQL？

> **满分回答模板：**
>
> 一句话：**常规 CRUD 用 ORM，复杂分析和批量用原生 SQL**。
>
> 展开：
> - 用 ORM：单表增删改查、简单关联、需要事务管理的业务逻辑。收益是类型安全、防注入、可维护。
> - 用原生 SQL：多表聚合报表、窗口函数、超过 3 层的子查询、百万级批量导入。收益是可控、可优化、可 `EXPLAIN`。
>
> 加分项：两者可以共存。SQLAlchemy 里 `session.execute(text("..."))` 就能执行原生 SQL，还能拿到 ORM 式的参数绑定，不必二选一。

---

## 9. 本章小结

三句话记住这一章：

1. **Engine 建一次，Session 建很多次。**
2. **模型是类，列是 `mapped_column`，`Mapped[T]` 是类型。**
3. **改属性不发 SQL，commit 才发，而且只发变化的列。**

### 验收清单

跑通下面四条，第三章就算过关：

- [ ] 不查资料，能写出 `Base` / `Model` / `engine` / `Session` 四件套
- [ ] 能解释 `session.get(User, 1)` 和 `select(User).where(...)` 的区别
- [ ] 能说出赋相同值为什么不会发 UPDATE
- [ ] 能解释 `server_default` 和 `default` 生成的 DDL 差在哪

### 下一章预告

第四章开始，我们会把这套东西用到真业务里：

- `session.add()` / `delete()` / `commit()`
- 把操作封装进 `app/services/`
- 分页、条件查询、批量操作
- 软删除 vs 硬删除的业务取舍

---

<small>相关：[番外01 -- Alembic 数据库迁移](番外01%20--%20Alembic%20数据库迁移.md) · [第二章 -- Python 数据库连接池](第二章%20--%20Python%20数据库连接池.md)</small>
