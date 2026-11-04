# 第三章 · SQLAlchemy ORM 基础

> **一句话**：ORM 就是把「发 SQL、拿字典、自己拼字符串」换成「拿对象、改属性、提交」。

**学习方式**：本文分六块 —— 先讲知识（一），再给 4 个能跑的例子（二），然后是业务场景（三）、报错排查（四）、自测题（五）、总结与速查卡（六）。第一块读完就能跑案例 1，不用等全部读完。

**分几次学**（不用一口气读完）：

| 第几次 | 干什么 | 用时 | 读到哪 |
| --- | --- | --- | --- |
| 第 1 次 | 只读知识，不写代码 | 15 分钟 | 一、1.1 ~ 1.6 |
| 第 2 次 | 跑 4 个案例 + 做「改一改」 | 20 分钟 | 二、案例 1 ~ 4 |
| 第 3 次 | 看业务场景 + 自测 3 题 | 10 分钟 | 三、五 |
| 以后 | 只翻章末速查卡 | 1 分钟 | 六、速查卡 |

---

# 一、这一章讲什么

## 1.1 四个角色

```plain
你的代码
   │  user = session.get(User, 1)
   ▼
┌────────────┐
│  Session   │  工作单元：管事务、管对象状态
└─────┬──────┘
      │ 要用连接时才借
      ▼
┌────────────┐
│   Engine   │  进程级唯一，内部持有一个连接池
└─────┬──────┘
      │
      ▼
   PyMySQL → MySQL 8.0
```

| 角色 | 一句话 | 建几个 |
| --- | --- | --- |
| Engine | 连接池的持有者 | 全进程 1 个 |
| Base | 模型登记册 | 全进程 1 个 |
| Model | 一个类 = 一张表 | 一张表 1 个 |
| Session | 一次业务操作的工作单元 | 每次操作 1 个 |

## 1.2 Engine：别每次请求都建

`create_engine(url)` 是重对象，创建时会把整个连接池初始化好。写进函数体、每个请求建一次，是最常见的性能事故。

```python
engine = create_engine(url, pool_pre_ping=True)  # 探活，解决 MySQL 8 小时断连
```

> 💡 这一行能省掉一整类"服务空闲一夜，第二天第一个请求 500"的事故——它和第二章的 `ping=1` 是同一件事，只是换了个名字。

> 🔗 想验证：**案例 1**（Engine 有没有真的建起来）

连接池参数的细节在第二章讲过，这里只需要记住：**Engine 全进程建一次**。

## 1.3 Base：模型必须被 import 才会注册

```python
class Base(DeclarativeBase):
    pass
```

它看着是空类，实际持有 `Base.metadata`——「本进程注册了哪些表」的登记表。每个子类自动登记。

⚠️ 写了 `app/models/order.py` 却没在任何地方 import，这张表就不在 `metadata` 里，迁移和建表都会漏掉它。所以 `app/models/__init__.py` 要把每个模型都 export 一次。

> 🔗 想验证：**案例 4**（`app/models/__init__.py` 是怎么 export 的）

## 1.4 Model：类型声明和列定义是两件事

```python
id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    └─ Python 侧 ─┘            └──── 数据库侧 ────┘
```

- `Mapped[int]` 决定 `user.id` 是 `int`（给 IDE 和类型检查器看）
- `mapped_column(...)` 决定建表时是 `INT UNSIGNED`（给数据库看）

**类型对照**：

| Python | SQLAlchemy | MySQL | 注意 |
| --- | --- | --- | --- |
| `int` | `INTEGER(unsigned=True)` | `INT UNSIGNED` | 必须从 `sqlalchemy.dialects.mysql` 导入 |
| `str` | `String(50)` | `VARCHAR(50)` | 必须给长度 |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` | 金额只用它，不用 `Float` |
| `bool` | `TINYINT(1)` | `TINYINT(1)` | 对应 `is_deleted` |
| `datetime` | `DateTime` | `DATETIME` | 不带时区 |

**`default` 和 `server_default` 的区别**（实测生成的建表语句）：

```sql
-- server_default=text("0.00")
balance NUMERIC(10, 2) NOT NULL DEFAULT (0.00)    ← DDL 里有 DEFAULT

-- default=Decimal("0.00")
balance NUMERIC(10, 2) NOT NULL                    ← DDL 里什么都没有
```

想和数据库结构一致，用 `server_default`；`default` 只是 Python 侧兜底，不进表结构。

> 🔗 想验证：**案例 1**（`User` 模型怎么写）、**案例 2**（对象和字典差在哪）

## 1.5 Session：不线程安全

```python
with Session(engine) as session:
    user = session.get(User, 1)
```

一次业务操作一个 Session。它管三件事：事务边界、身份映射（同 id 查两次返回同一对象）、脏检查。

⚠️ 别跨线程共享 Session。

> 🔗 想验证：**案例 1**（`with Session(engine)` 的写法与关闭）

## 1.6 脏检查：本章最反直觉的地方

改了对象的属性，**不会立刻发 SQL**。SQLAlchemy 只把对象标记为「脏」，等 `commit()` / `flush()` 时才逐字段对比快照，决定写不写。

两个反直觉的结论：

1. 赋一个**相同**的值，对象进了 dirty 集合，但 flush 时不发 UPDATE
2. 赋一个**不同**的值，UPDATE 只带变化的那一列，不是整行覆盖

> 💡 记住这个顺序：**改属性 → 只打标记；commit → 对比快照 → 才发 SQL**。搞混这两步，就会误以为"我改了怎么没生效"或"我没改怎么被覆盖了"。

这两条在案例 3 里可以亲眼看到。

> 🔗 想验证：**案例 3**（用 `event` 抓真实 SQL，看它发不发 UPDATE）

---

# 二、四个可执行案例

| 案例 | 文件 | 验证什么 | 用时 |
| --- | --- | --- | --- |
| 1 | `01_first_query.py` | 最小闭环，查出第一条数据 | 3 分钟 |
| 2 | `02_pymysql_vs_orm.py` | 字典 vs 对象，差别到底在哪 | 3 分钟 |
| 3 | `03_dirty_check.py` | 脏检查与 UPDATE 触发条件 | 5 分钟 |
| 4 | `04_use_app_model.py` | 脚本版 vs 工程版，只差一个 import | 3 分钟 |

## 跑之前的准备

所有案例都从环境变量读连接信息：

```bash
cd D:/github_repository/mysql-learning      # 必须在仓库根目录
export MYSQL_PASSWORD=你的密码
```

> 案例 4 会 import `app` 包，所以必须在仓库根目录执行；其它三个在哪跑都行。

---

## 案例 1 · 第一条查询

> 🔗 对应知识点：**1.2 Engine · 1.3 Base · 1.4 Model · 1.5 Session**

**验证什么**：Engine / Base / Model / Session 四个对象能不能串起来。

**文件**：`chapters/ch03/code/01_first_query.py`

**核心代码**（完整版见文件）：

```python
engine = create_engine(url)                 # ① 引擎

class Base(DeclarativeBase):                # ② 登记册
    pass

class User(Base):                           # ③ 模型
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    # ... 其余列

with Session(engine) as session:            # ④ 工作单元
    user = session.get(User, 1)
```

**怎么跑**：

```bash
python chapters/ch03/code/01_first_query.py
```

**你会看到**：

```plain
【1】按主键查一条
    返回值类型： User
    对象本身   ： <User id=1 username='张三' balance=888.00>
    取属性     ： 张三 | 888.00 | 13800000001

【2】查不到时返回什么
    session.get(User, 999999) -> None
    没有抛异常，只是 None

【3】把整张表取回来（每行都是一个对象）
    <User id=1 username='张三' balance=888.00>
    <User id=2 username='李四' balance=400.00>
    <User id=3 username='王五' balance=100.00>
```

**能学到什么**：

- `session.get()` 返回的是 **对象**，不是元组也不是字典
- 查不到返回 `None`，**不抛异常**——所以判断"用户不存在"写 `if user is None` 就行
- 一行数据被翻译成对象后，列名变成了属性名，IDE 能补全
- `__repr__` 不是必须的，但没有它打印出来是 `<User object at 0x...>`，调试很痛苦

**改一改**（1 分钟）：把 `session.get(User, 1)` 里的 1 改成 2，看输出变成谁；再改成 999999，确认拿到 `None` 而不是报错。

---

## 案例 2 · PyMySQL 和 ORM 的差别

> 🔗 对应知识点：**1.1 四个角色**（同一件事的两种写法）

**验证什么**：同一行数据，两种写法拿回来的东西到底差在哪。

**文件**：`chapters/ch03/code/02_pymysql_vs_orm.py`

**核心代码**：

```python
# A. PyMySQL：自己写 SQL，拿回字典
cur.execute("SELECT * FROM users WHERE id = %s", (1,))
row = cur.fetchone()
print(row["username"])

# B. ORM：不写 SQL，拿回对象
user = session.get(User, 1)
print(user.username)
```

**怎么跑**：

```bash
python chapters/ch03/code/02_pymysql_vs_orm.py
```

**你会看到**：

```plain
【A】PyMySQL
返回类型  : dict
内容      : {'id': 1, 'username': '张三', 'phone': '13800000001',
             'balance': Decimal('888.00'), 'is_deleted': 0, ...}
怎么取值  : row['username'] = 张三
有没有补全: 没有，键名写错要到运行时才报 KeyError

【B】ORM
返回类型  : User
内容      : <User id=1 username='张三' balance=888.00>
怎么取值  : user.username = 张三
有没有补全: 有，IDE 能提示 User 的所有属性
```

**能学到什么**：

| 维度 | PyMySQL | ORM |
| --- | --- | --- |
| 数据载体 | `dict` | `User` 对象 |
| 字段类型 | 运行时才知道 | 写代码时就知道 |
| 改数据 | 自己拼 `UPDATE` | `user.balance = 100` |
| 复杂查询 | 直接写，爽 | 要绕一层 |

> ORM 替代的是**重复的样板 SQL**，不是复杂查询。报表、多表聚合照样手写。

**改一改**（2 分钟）：在 `02_pymysql_vs_orm.py` 里给 User 加一个 `vip` 属性（用 `@property`，不是列），打印 `user.vip`，感受"对象能挂方法，字典不能"。

---

## 案例 3 · 脏检查与 UPDATE 触发条件

> 🔗 对应知识点：**1.6 脏检查**

**验证什么**：改属性到底什么时候才真的写库。

**文件**：`chapters/ch03/code/03_dirty_check.py`

这个案例用 `event` 监听器把 ORM 实际发出的 SQL 抓了下来：

```python
@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, parameters, context, executemany):
    _captured.append(" ".join(statement.split()))
```

**怎么跑**：

```bash
python chapters/ch03/code/03_dirty_check.py
```

> 全程不 commit，最后 rollback，**不会改坏你的数据**。

**你会看到**：

```plain
--- ① 只是查询 ---
    balance = 888.00
    session.dirty = IdentitySet([])

--- ② 赋一个相同的值，然后 flush ---
    session.dirty = IdentitySet([<User object at 0x...>])   ← 对象进去了
    实际发出去的 SQL：（没有 UPDATE）
    结论：进了 dirty 集合 ≠ 一定会发 UPDATE

--- ③ 赋一个不同的值，然后 flush ---
    SQL: UPDATE users SET balance=%(balance)s WHERE users.id = %(users_id)s
    结论：只 UPDATE 变化的那一列，不是整行覆盖

--- ④ rollback 把内存修改一起丢弃 ---
    回滚前（内存里）：777.00
    回滚后（重新查）：888.00
```

**能学到什么**：

- 改属性只是**打标记**，此刻数据库毫不知情
- flush 时会对比属性快照，值没变就跳过
- UPDATE 只带变化的列 → 多人改同一行不同字段不会互相覆盖
- 但同一列的并发冲突，ORM 管不了，要靠乐观锁或 `SELECT ... FOR UPDATE`
- `rollback()` 会连内存里的修改一起丢掉

**改一改**（2 分钟）：把 ③ 里的 `777.00` 改成当前值（`888.00`），再跑一次——你会看到 SQL 变回"没有 UPDATE"，印证第 ② 步的结论。

---

## 案例 4 · 脚本版和工程版，只差一个 import

> 🔗 对应知识点：**1.2 Engine · 1.3 Base**（它们在 `app/` 里长什么样）

**验证什么**：`app/` 里的那份模型，用起来和案例 1 的本地模型有什么区别。

**文件**：`chapters/ch03/code/04_use_app_model.py`

**核心代码**：

```python
from app.models import User          # 模型来自 app/
from app.db.session import SessionLocal   # 会话来自 app/

with SessionLocal() as db:
    user = db.get(User, 1)
```

**怎么跑**：

```bash
python chapters/ch03/code/04_use_app_model.py
```

**你会看到**：

```plain
【1】按主键查（和案例 1 写法一模一样）
    <User id=1 username='张三' balance=888.00>

【2】查全部
    <User id=1 username='张三' balance=888.00>
    <User id=2 username='李四' balance=400.00>
    <User id=3 username='王五' balance=100.00>
```

**能学到什么**：

| | 案例 1 | 案例 4 |
| --- | --- | --- |
| 模型定义在哪 | 脚本里 | `app/models/user.py` |
| 引擎从哪来 | 脚本里 `create_engine` | `app/db/engine.py` |
| 会话从哪来 | `Session(engine)` | `app/db/session.py` |
| 业务代码要关心这些吗 | 要 | **不要** |

这就是分层的价值：业务代码只写 `db.get(User, 1)`，不关心连接池多大、密码从哪读、`Base` 有几个子类。

**改一改**（2 分钟）：在 `04_use_app_model.py` 里把 `from app.models import User` 换成 `from app.models.user import User`，跑通后再换回来——两条 import 路径都有效，感受一下"包 __init__ 做了什么"。

---

# 三、业务场景对话

**Q：查一条数据，用 `session.get()` 还是 `select()`？**

`get()` 只认主键，好处是**先查身份映射**——对象已经在 Session 里就直接返回，不查库。所以"按 id 取"永远用 `get()`。

按非主键条件查（用户名、手机号）只能用 `select()`：

```python
user = session.execute(
    select(User).where(User.username == "张三")
).scalar_one_or_none()
```

> 💡 用 `scalar_one_or_none()` 而不是 `scalar_one()`：前者查不到返回 `None`，后者直接抛异常。

**Q：公司里为什么禁止在循环里 `session.get()`？**

这是典型的 **N+1 查询**：循环 100 次就是 100 次数据库往返。

```python
# ⚠️ 别这样
for uid in user_ids:
    print(session.get(User, uid).username)

# 💡 一次捞回来
users = session.scalars(select(User).where(User.id.in_(user_ids))).all()
```

**Q：ORM 和原生 SQL 怎么分工？**

| 场景 | 用什么 |
| --- | --- |
| 常规 CRUD、单表、简单关联 | ORM |
| 报表、多表聚合、窗口函数 | 原生 SQL（`session.execute(text(...))`） |
| 百万级批量导入 | 原生 SQL |
| 需要精确控制执行计划 | 原生 SQL |

一句话：**ORM 替代的是样板 SQL，不是复杂 SQL。**

---

# 四、跑不起来怎么办

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `Access denied for user 'root'` | 没设 `MYSQL_PASSWORD` 或密码错 | `export MYSQL_PASSWORD=你的密码` |
| `Table 'xxx.users' doesn't exist` | 连错库 | 检查 `MYSQL_DATABASE`，本章要 `learn_mysql` |
| `NoSuchModuleError: Can't load plugin ... mysql.pymysql` | 没装 PyMySQL | `pip install PyMySQL` |
| `TypeError: 'unsigned' is an invalid keyword argument` | 用了通用 `INTEGER` | 从 `sqlalchemy.dialects.mysql` 导入 |
| `ArgumentError: Could not parse SQLAlchemy URL` | 密码含 `@ : / #` | 用 `quote_plus()` 编码 |
| 案例 4 报 `ModuleNotFoundError: No module named 'app'` | 没在仓库根目录跑 | `cd` 到仓库根目录再执行 |
| 打印出 `<User object at 0x...>` | 没写 `__repr__` | 无关紧要，写完就好看 |

---

# 五、自测：3 道面试题

### Q1. Engine 和 Session 的区别是什么？

> **满分回答模板**
>
> 一句话：**Engine 管连接，Session 管事务和对象**。
>
> 展开三点：
> 1. **生命周期不同**——Engine 是进程级的，应用启动建一次，跟着进程走；Session 是请求级或操作级的，用完就关。
> 2. **职责不同**——Engine 内部持有连接池，负责"怎么连数据库"；Session 是工作单元，负责"这次业务做了哪些操作、要不要提交"。
> 3. **线程安全性不同**——Engine 线程安全，可以共享；Session 不是，必须一个线程/请求一个。
>
> 加分项：Session 并不会一直占着连接，它只在执行 SQL 时才向 Engine 借，用完立刻还——这一点和第二章的池化是同一套机制。

### Q2. ORM 的"脏检查"是怎么工作的？什么时候发 UPDATE？

> **满分回答模板**
>
> 一句话：**改属性只打标记，flush 时才对比快照决定发不发 SQL**。
>
> 展开：
> 1. 对象从库里查出来时，SQLAlchemy 保留一份属性快照；
> 2. 执行 `user.balance = 100`，对象进入 Session 的 dirty 集合，但**此刻没有任何 SQL 发出**；
> 3. `commit()` / `flush()` 时逐字段对比快照：没变就跳过，变了就生成 UPDATE，且**只带变化的列**。
>
> 加分项：因为只更新变化列，多人同时改同一行的不同字段不会互相覆盖；但同一字段的并发冲突仍然要靠乐观锁或 `SELECT ... FOR UPDATE` 解决，这是 ORM 管不了的。我们实测过：赋相同的值，flush 时确实不发 UPDATE。

### Q3. 什么时候该用 ORM，什么时候该写原生 SQL？

> **满分回答模板**
>
> 一句话：**常规 CRUD 用 ORM，复杂分析和批量用原生 SQL**。
>
> 展开：
> - 用 ORM：单表增删改查、简单关联、需要事务管理的业务逻辑。收益是类型安全、防注入、可维护。
> - 用原生 SQL：多表聚合报表、窗口函数、深层子查询、百万级批量导入。收益是可控、可优化、可 `EXPLAIN`。
>
> 加分项：两者可以共存，不是二选一。SQLAlchemy 里 `session.execute(text("..."))` 就能执行原生 SQL，还带参数绑定。

---

# 六、本章总结

**三句话**：

1. Engine 建一次，Session 建很多次
2. 模型是类，列用 `mapped_column`，`Mapped[T]` 管类型
3. 改属性不发 SQL，commit 才发，而且只发变化的列

**验收清单**（能不看文档答出来就算过关）：

- [ ] 说出 Engine / Base / Model / Session 各自负责什么
- [ ] 解释 `session.get(User, 1)` 和 `select(User).where(...)` 的区别
- [ ] 解释赋相同值为什么不会发 UPDATE
- [ ] 说出 `server_default` 和 `default` 生成的 DDL 差在哪

---

## 速查卡（一周后回来看这里）

**四件套骨架**

```python
engine = create_engine(url, pool_pre_ping=True)     # 全局一个

class Base(DeclarativeBase):                        # 全局一个
    pass

class User(Base):                                   # 一张表一个
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)

with Session(engine) as session:                    # 一次操作一个
    session.get(User, 1)
```

**常用操作**

| 想干什么 | 写法 |
| --- | --- |
| 按主键查 | `session.get(User, 1)`（查不到返回 `None`） |
| 按条件查 | `session.execute(select(User).where(...)).scalar_one_or_none()` |
| 批量查 | `session.scalars(select(User).where(User.id.in_(ids))).all()` |
| 改字段 | `user.balance = 100` 然后 `session.commit()` |
| 撤销 | `session.rollback()` |

**三句话**

1. Engine 建一次，Session 建很多次
2. 改属性不发 SQL，commit 才发，而且只发变化的列
3. `server_default` 进 DDL，`default` 只在 Python 侧

**类型对照（最常用的五个）**

| Python | SQLAlchemy | MySQL |
| --- | --- | --- |
| `int` | `INTEGER(unsigned=True)` | `INT UNSIGNED` |
| `str` | `String(50)` | `VARCHAR(50)` |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` |
| `bool` | `TINYINT(1)` | `TINYINT(1)` |
| `datetime` | `DateTime` | `DATETIME` |

**下一步**：第四章用 `session.add()` / `delete()` 写真正的增删改查，并把这些操作封装进 `app/services/`。

---

<small>相关：[番外01 -- Alembic 数据库迁移](../../extras/notes/01-Alembic%20数据库迁移.md) · [第二章 -- Python 数据库连接池](../../ch02/notes/Python%20数据库连接池.md)</small>
