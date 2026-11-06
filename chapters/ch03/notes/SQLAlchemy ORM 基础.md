# 第三章 · SQLAlchemy ORM 基础

## 3.1 学习目标

本章讲解 SQLAlchemy 2.0 的基础用法,具体包括：

1. 理解 ORM 的作用,以及它与直接执行 SQL 的区别
2. 掌握 Engine、Base、Model、Session 四个核心对象的职责与创建方式
3. 能够用 2.0 语法定义模型,并把 MySQL 的列类型正确映射为 SQLAlchemy 类型
4. 能够通过 Session 完成最基本的查询
5. 理解"脏检查"机制,知道修改属性与提交事务之间的关系

前置知识：第一章（SQL 基础）、第二章（连接池）。

> **本章的读法**：正文是教材写法,先给定义再给例子。每个关键概念后面有一个「通俗理解」框,正文看不懂时先看那个框。
> 每节末尾标了可运行的案例文件,建议边读边跑。

---

## 3.2 ORM 与 SQLAlchemy

### 3.2.1 什么是 ORM

ORM（Object Relational Mapping,对象关系映射）是一种把数据库表映射为编程语言对象的技术。

映射关系如下：

| 数据库概念 | 对应到 Python |
| --- | --- |
| 一张表 | 一个类（Model） |
| 表里的一行 | 一个对象（实例） |
| 表里的一个字段 | 对象的一个属性 |

建立映射之后,查询一行数据得到的不再是字典,而是一个对象：

```python
# 不用 ORM
cur.execute("SELECT * FROM users WHERE id = %s", (1,))
row = cur.fetchone()
name = row["username"]

# 用 ORM
user = session.get(User, 1)
name = user.username
```

> **通俗理解**：以前你发 SQL、拿回一个字典、用 `row["username"]` 取值。现在你拿回一个对象,直接用 `user.username`。数据库那一行数据被"翻译"成了 Python 对象,字段名变成了属性名,编辑器还能自动提示。

### 3.2.2 ORM 的优缺点

| 优点 | 说明 |
| --- | --- |
| 减少重复 SQL | 常规增删改查不必手写 SQL |
| 类型安全 | 字段有类型,写错属性名编辑器会提示 |
| 防注入 | 参数由框架绑定,不会拼字符串 |
| 便于换库 | 换数据库时业务代码基本不改 |

| 缺点 | 说明 |
| --- | --- |
| 复杂查询表达力弱 | 多表聚合、窗口函数仍然手写 SQL 更清晰 |
| 隐藏了 SQL 开销 | 不开启回显时,你不知道到底发了几条 SQL |
| 批量操作较慢 | 逐对象实例化有额外开销 |

结论：**ORM 替代的是重复的样板 SQL,不是复杂查询。**

### 3.2.3 SQLAlchemy 的四个核心对象

| 对象 | 职责 | 创建次数 |
| --- | --- | --- |
| `Engine` | 管理数据库连接与连接池 | 全程序 1 个 |
| `Base` | 所有模型的基类,持有表结构元数据 | 全程序 1 个 |
| `Model` | 描述一张表的字段 | 每张表 1 个 |
| `Session` | 一次操作的工作单元,负责事务与对象状态 | 每次操作 1 个 |

它们的调用关系：

```plain
        你的代码
           │
           ▼
   ┌───────────────┐
   │    Session    │  一次操作的工作台
   └───────┬───────┘
           │ 执行 SQL 时向 Engine 借连接
           ▼
   ┌───────────────┐
   │    Engine     │  持有连接池
   └───────┬───────┘
           ▼
        MySQL 8.0
```

> **通俗理解**：Engine 是"通到数据库的水管",建一次一直用；Session 是"每次办事用的窗口",办完就关；Base 是"户口本",负责记录有哪些表；Model 是"表格模板",定义每张表长什么样。

### 3.2.4 本章使用的数据表

本章只使用 `users` 表（第一章建,第二章也用过）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `INT UNSIGNED` | 主键,自增 |
| `username` | `VARCHAR(50)` | 用户名,唯一 |
| `phone` | `VARCHAR(20)` | 手机号,唯一 |
| `balance` | `DECIMAL(10,2)` | 余额 |
| `is_deleted` | `TINYINT(1)` | 软删除标记 |
| `created_at` | `DATETIME` | 注册时间 |

---

## 3.3 Engine

### 3.3.1 作用

Engine 负责管理数据库连接。它内部维护一个连接池,程序运行期间只创建一次。

### 3.3.2 创建方法

```python
from sqlalchemy import create_engine

engine = create_engine(
    "mysql+pymysql://root:密码@localhost:3306/learn_mysql?charset=utf8mb4",
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

连接字符串的格式：

```plain
dialect+driver://用户名:密码@主机:端口/数据库名?字符集
    │       │
   mysql   pymysql
```

| 参数 | 作用 |
| --- | --- |
| `pool_pre_ping` | 借出连接前先探活,解决 MySQL 8 小时断连 |
| `pool_recycle` | 连接存活超过指定秒数后自动重建 |

> **通俗理解**：`create_engine` 只是把"连哪个库、用什么账号"记下来,并准备一个连接池。**它不会立刻连接数据库**——真正连库发生在第一次执行 SQL 的时候。这一点可以用案例 6 第 ① 步验证。

### 3.3.3 使用注意

Engine 必须全局唯一。常见错误是把 `create_engine` 写在函数体内,导致每次请求都重新初始化连接池：

```python
# 错误写法
def get_user():
    engine = create_engine(url)    # 每次调用都建一个新池,性能灾难
    ...

# 正确写法：在 project/app/db/engine.py 建一次,别处直接 import
from app.db.engine import engine
```

案例文件：`chapters/ch03/code/06_under_the_hood.py`（第 ① 步演示连接池状态）

---

## 3.4 Base 与 Model

### 3.4.1 Base 的作用

`Base` 是所有模型的父类,它持有的 `Base.metadata` 记录了"本程序注册了哪些表"。

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

每个继承 `Base` 的类都会自动注册到 `metadata` 中。

**注意**：模型必须被 import 过才会注册。如果写了 `project/app/models/order.py` 但没有地方 import 它,`metadata` 里就没有这张表,建表和迁移都会漏掉。

### 3.4.2 定义模型

SQLAlchemy 2.0 推荐使用类型标注的写法：

```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0.00"))
    is_deleted: Mapped[bool] = mapped_column(TINYINT(1), server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
```

一行定义包含两部分：

| 部分 | 给谁看 | 作用 |
| --- | --- | --- |
| `Mapped[int]` | 编辑器、类型检查器 | 声明 Python 侧类型 |
| `mapped_column(...)` | 数据库 | 声明列的类型、约束、默认值 |

> **通俗理解**：左边告诉 Python"这个属性是整数",右边告诉数据库"这一列是 INT UNSIGNED"。两边合起来,代码里是类型安全的属性,建表时是准确的列定义。

### 3.4.3 类型映射

| Python 类型 | SQLAlchemy 类型 | MySQL 类型 | 说明 |
| --- | --- | --- | --- |
| `int` | `INTEGER(unsigned=True)` | `INT UNSIGNED` | 必须从 `sqlalchemy.dialects.mysql` 导入 |
| `str` | `String(50)` | `VARCHAR(50)` | 需要指定长度 |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` | 金额必须用它,不能用 `Float` |
| `bool` | `TINYINT(1)` | `TINYINT(1)` | 用于标记字段 |
| `datetime` | `DateTime` | `DATETIME` | 不带时区 |

### 3.4.4 default 与 server_default

两者都能设置默认值,但生成的建表语句不同：

```sql
-- server_default=text("0.00")
balance NUMERIC(10, 2) NOT NULL DEFAULT (0.00)     ← 建表语句里有 DEFAULT

-- default=Decimal("0.00")
balance NUMERIC(10, 2) NOT NULL                     ← 建表语句里什么都没有
```

| | `server_default` | `default` |
| --- | --- | --- |
| DEFAULT 是否写进建表语句 | 是 | 否 |
| 谁来填值 | 数据库 | Python（INSERT 前） |
| 绕过 ORM 直接 INSERT 时 | 生效 | 不生效 |

要保证模型与表结构一致,应使用 `server_default`。

> **通俗理解**：`server_default` 是"写进表格模板里的默认值",谁来填都得按这个来；`default` 只是"Python 帮你填一下",数据库那边其实没有默认值。所以想让表结构和代码对得上,用前者。

案例文件：`chapters/ch03/code/01_first_query.py`（模型定义）、`04_use_app_model.py`（工程版模型）

---

## 3.5 Session

### 3.5.1 作用

Session 是一次操作的工作单元,负责三件事：

1. 管理事务边界（提交、回滚）
2. 维护对象状态（新增、修改、删除）
3. 提供身份映射（同一个 id 只对应一个对象）

### 3.5.2 使用方式

推荐使用 `with` 语句,它会自动关闭：

```python
from sqlalchemy.orm import Session

with Session(engine) as session:
    user = session.get(User, 1)
    print(user.username)
# 退出 with 时自动 close,连接归还连接池
```

### 3.5.3 生命周期

| 阶段 | 说明 |
| --- | --- |
| 创建 | 每次业务操作用一个新的 Session |
| 使用 | 执行查询、修改对象,此时不一定占用连接 |
| 关闭 | `close()` 归还连接,Session 不再可用 |

**注意**：Session 不是线程安全的。一个线程一个 Session,或一个请求一个 Session,不能共享。

> **通俗理解**：Session 像银行办事窗口——取号、办事、走人。你不会一直占着窗口不走,Session 也一样,用完要关,把数据库连接还回池子。

案例文件：`chapters/ch03/code/01_first_query.py`

---

## 3.6 查询数据

### 3.6.1 按主键查询

```python
user = session.get(User, 1)
```

返回一个 `User` 对象；如果该 id 不存在,返回 `None`,**不抛异常**。

### 3.6.2 条件查询

```python
from sqlalchemy import select

users = session.scalars(select(User).where(User.balance > 200)).all()
```

常用子句对应关系：

| SQL | SQLAlchemy |
| --- | --- |
| `SELECT * FROM users` | `select(User)` |
| `WHERE balance > 200` | `.where(User.balance > 200)` |
| `ORDER BY balance DESC` | `.order_by(User.balance.desc())` |
| `LIMIT 10` | `.limit(10)` |
| `OFFSET 20` | `.offset(20)` |
| `COUNT(*)` | `select(func.count()).select_from(User)` |

> **通俗理解**：ORM 没有发明新东西,它只是把 SQL 的关键字变成了方法名。你会写 `WHERE`,就等于会写 `.where()`。

案例文件：`chapters/ch03/code/05_sql_vs_orm.py`（同一操作两种写法并排对比）

### 3.6.3 示例与运行结果

示例文件：`chapters/ch03/code/01_first_query.py`

```python
with Session(engine) as session:
    user = session.get(User, 1)
    print(user.username, user.balance)
```

运行结果：

```plain
【1】按主键查一条
    返回值类型： User
    对象本身   ： <User id=1 username='张三' balance=888.00>
    取属性     ： 张三 | 888.00 | 13800000001

【2】查不到时返回什么
    session.get(User, 999999) -> None
    没有抛异常,只是 None

【3】把整张表取回来（每行都是一个对象）
    <User id=1 username='张三' balance=888.00>
    <User id=2 username='李四' balance=400.00>
    <User id=3 username='王五' balance=100.00>
```

---

## 3.7 脏检查机制

### 3.7.1 现象

修改对象的属性后,数据库**不会立即更新**,而是等到 `commit()` 时才执行更新。

```python
user = session.get(User, 1)
user.balance = 100        # 此刻没有 SQL 发出
session.commit()          # 这里才 UPDATE
```

### 3.7.2 原理

Session 在三个时刻工作：

```plain
user.balance = 100
      │
      ▼
① 把对象标记为"脏"（dirty）        ← 不发 SQL
      │
      ▼
session.commit()
      │
      ▼
② 把当前值与加载时的快照逐字段比对   ← 对比发生在内存里
      │
      ├── 没变 → 跳过
      └── 变了 → 生成 UPDATE,只带变化的列
      │
      ▼
③ 提交事务
```

### 3.7.3 示例与运行结果

示例文件：`chapters/ch03/code/03_dirty_check.py`

该案例通过事件监听抓取了实际发出的 SQL：

```plain
--- ② 赋一个相同的值,然后 flush ---
    session.dirty = IdentitySet([<User object at 0x...>])   ← 对象进了脏集合
    实际发出去的 SQL：（没有 UPDATE）

--- ③ 赋一个不同的值,然后 flush ---
    SQL: UPDATE users SET balance=%(balance)s WHERE users.id = %(users_id)s

--- ④ rollback 把内存修改一起丢弃 ---
    回滚前（内存里）：777.00
    回滚后（重新查）：888.00
```

两个结论：

1. 赋**相同**的值,对象进了 dirty 集合,但不会生成 UPDATE；
2. UPDATE **只包含变化的列**,不是整行覆盖。

> **通俗理解**：像在 Word 里改文档——打字的时候文件没变,按保存才写盘,而且只写改动过的段落。`commit()` 就是那个保存键。

### 3.7.4 补充：身份映射

在同一个 Session 中,同一个 id 只会对应一个对象：

```plain
a = db.get(User, 2)   →  <User id=2 username='李四' balance=400.00>
b = db.get(User, 2)   →  <User id=2 username='李四' balance=400.00>
a is b ?  True
这两次 get 一共发了 1 条 SQL
```

第二次查询没有访问数据库,而是直接从 Session 缓存返回。

案例文件：`chapters/ch03/code/06_under_the_hood.py`（第 ⑦ 步）

---

## 3.8 常见错误

| 错误信息 | 原因 | 解决方法 |
| --- | --- | --- |
| `NoSuchModuleError: Can't load plugin: mysql.pymysql` | 未安装 PyMySQL 或连接串写错 | `pip install PyMySQL`,连接串用 `mysql+pymysql://` |
| `Table 'xxx.users' doesn't exist` | 连接到了错误的数据库 | 检查连接串中的数据库名 |
| `TypeError: 'unsigned' is an invalid keyword argument` | 使用了通用的 `INTEGER` | 从 `sqlalchemy.dialects.mysql` 导入 |
| `ArgumentError: Could not parse SQLAlchemy URL` | 密码含特殊字符未编码 | 使用 `quote_plus()` |
| `DetachedInstanceError` | Session 关闭后访问对象属性 | 在 `with` 块内取完所需字段 |
| 打印出 `<User object at 0x...>` | 未定义 `__repr__` | 添加 `__repr__` 方法 |

---

## 3.9 本章小结

1. ORM 把表映射为类、行映射为对象、字段映射为属性,替代的是样板 SQL,不是复杂查询。
2. Engine 管理连接池,全程序建一次；Session 是工作单元,每次操作用一个。
3. 模型定义中,`Mapped[T]` 声明 Python 类型,`mapped_column()` 声明数据库列。
4. 模型必须被 import 才会注册到 `Base.metadata`,否则建表和迁移会漏表。
5. 修改属性只打标记,`commit()` 时才比对快照并生成 UPDATE,且只带变化的列。

---

## 3.10 练习

1. 为 `users` 表补上 `email` 字段的模型定义（先不动数据库,只写模型）,思考 `String(100)` 是否够用。
2. 用 `select()` 写出"查询余额在 100 到 500 之间、按余额升序"的语句,并翻译成对应的 SQL。
3. 运行案例 3,把第 ③ 步改的值改回原值,观察是否还会生成 UPDATE。
4. 运行案例 6,回答：`db.add(user)` 之后、`db.commit()` 之前,数据库里有没有这条记录？

---

<small>相关：[第二章 -- Python 数据库连接池](../../ch02/notes/Python%20数据库连接池.md) · [第四章 -- 增删改查](../../ch04/notes/SQLAlchemy%20ORM%20CRUD.md)</small>
