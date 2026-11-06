# 第三章 · 从 SQL 到对象（大白话版）

> 这一章只讲一件事：**以前你发 SQL 拿字典，现在你拿对象改属性。**

---

## 这一章涉及哪些知识点

1. **四个角色**：Engine、Base、Model、Session 各是干什么的
2. **Engine**：一根一直通着的水管
3. **Base 和 Model**：上户口 + 表格模板
4. **Session**：取号办事，办完走人
5. **查第一条数据**：报个 id，直接拿到对象
6. **脏检查**：改在草稿上，提交才存档

每个知识点都是：**一句话结论 → 打个比方 → 看代码 → 记住一个坑**。

---

## 先看一张「比喻地图」

| 你要干的事 | 生活里的比方 | 对应代码 |
| --- | --- | --- |
| 连上数据库 | 铺一根水管，一直通着 | `create_engine(url)` |
| 告诉它有哪些表 | 上户口，登记一下 | `class Base(DeclarativeBase)` |
| 描述一行数据的字段 | 设计一张表格模板 | `class User(Base)` + `mapped_column` |
| 开一次操作 | 去银行取号，办完走人 | `Session(engine)` |
| 查一条数据 | 报身份证号，直接调档 | `session.get(User, 1)` |
| 改数据 | 在草稿上改字 | `user.balance = 100` |
| 让改动生效 | 交表存档 | `commit()` |

## 英文词小抄

| 英文 | 中文 | 一句人话 |
| --- | --- | --- |
| `Engine` | 引擎 | 管理数据库连接的对象，全程序只建一个 |
| `Base` | 基类 | 所有模型的共同父类，管着「有哪些表」 |
| `Model` | 模型 | 一个类对应一张表，一个属性对应一列 |
| `Session` | 会话 | 一次操作的工作台，办完要关 |
| `DeclarativeBase` | 声明式基类 | SQLAlchemy 2.0 推荐的写法，直接用就行 |
| `Mapped[int]` | 映射类型 | 告诉编辑器「这个属性是整数」 |
| `mapped_column` | 映射列 | 定义这一列在数据库里长什么样 |
| `commit` | 提交 | 把内存里的改动真正写进数据库 |
| `rollback` | 回滚 | 反悔，撤销这次没提交的改动 |
| `flush` | 刷写 | 把改动同步到数据库（还没提交） |
| `dirty` | 脏 | 被改过但还没提交的对象 |

---

## 知识点 1：四个角色 —— 一家小公司

**一句话**：操作数据库这件事，被拆成四个岗位，各干各的。

**打个比方**

把这套东西想成一家小公司：

| 岗位 | 对应代码 | 干什么 |
| --- | --- | --- |
| 水管工 | **Engine** | 负责把水管（连接）铺到数据库，只铺一次 |
| 户口本 | **Base** | 记录公司有哪些「表」，谁来都要登记 |
| 表格模板 | **Model** | 定义每张表长什么样：有哪些字段、什么类型 |
| 办事窗口 | **Session** | 你每次办事用的窗口，办完就走，不长期占着 |

它们的位置关系：

```plain
        你的代码
           │
           ▼
   ┌───────────────┐
   │    Session    │  办事窗口：一次业务的临时工作台
   └───────┬───────┘
           │ 要用连接时才去借
           ▼
   ┌───────────────┐
   │    Engine     │  水管工：持有连接池，全程序一个
   └───────┬───────┘
           ▼
        MySQL
```

**看代码**（20 行跑通，完整版见 `chapters/ch03/code/01_first_query.py`）

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engine = create_engine(url)          # ① 水管工
class Base(DeclarativeBase):         # ② 户口本
    pass
class User(Base):                    # ③ 表格模板
    __tablename__ = "users"
with Session(engine) as session:     # ④ 办事窗口
    ...
```

**记住一个坑**

**`create_engine` 只能建一次，别写在函数里。** 它一建就要初始化整个连接池，你每个请求建一次，等于每次都重新铺一遍水管。这是新手最常见的性能事故。

跑一遍：`python chapters/ch03/code/01_first_query.py`

---

## 知识点 2：Engine —— 一根一直通着的水管

**一句话**：Engine 就是那根通到数据库的水管，建一次，一直用。

**打个比方**

- 笨办法：每次洗手都重新铺一遍水管。
- 正常办法：管子铺好一直通着，洗手、洗菜、冲马桶都用它。

每次 `pymysql.connect()` 就是"重新铺管子"——要 TCP 握手、要认证、要初始化会话。第二章测过，建一次连接要 11 毫秒，而执行一条简单查询只要 0.5 毫秒。

**看代码**

```python
engine = create_engine(
    url,
    pool_pre_ping=True,      # 借出前先探一下管子通不通
    pool_recycle=3600,       # 管子用了一小时就换新的
)
```

> 💡 `pool_pre_ping=True` 能省掉一整类事故：MySQL 默认 8 小时没动静就把连接掐了，第二天第一个请求拿到一根死管子。加上这个，借出前先试一下，断了自动重接。

**记住一个坑**

**Engine 要全局只有一个。** 在 `app/db/engine.py` 里建，别的地方 `from app.db.engine import engine` 拿来用，不要自己再 `create_engine` 一次。

---

## 知识点 3：Base 和 Model —— 上户口 + 表格模板

**一句话**：Base 是户口本（记录有哪些表），Model 是表格模板（定义每张表长什么样）。

**打个比方**

- **Base**：公司的户口本。每张表都要在它那儿登记一次，不然公司不知道你存在。
- **Model**：一张"人员登记表"的模板——姓名那一栏多宽、年龄是不是数字、入职时间能不能留空。

**看代码**

```python
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"                                      # 表名

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2))
```

两个东西必须成对出现：

| 写法 | 给谁看的 | 作用 |
| --- | --- | --- |
| `Mapped[int]` | 编辑器、类型检查 | 让 `user.id` 自动识别成整数 |
| `mapped_column(...)` | 数据库 | 建表时变成 `INT UNSIGNED` |

**类型怎么对应**

| Python 类型 | 写法 | 数据库里 |
| --- | --- | --- |
| `int` | `INTEGER(unsigned=True)` | `INT UNSIGNED` |
| `str` | `String(50)` | `VARCHAR(50)` |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` |
| `bool` | `TINYINT(1)` | `TINYINT(1)` |
| `datetime` | `DateTime` | `DATETIME` |

**`default` 和 `server_default` 的区别**

一个进建表语句，一个不进：

```sql
-- server_default=text("0.00")
balance NUMERIC(10, 2) NOT NULL DEFAULT (0.00)    ← 建表语句里有默认值

-- default=Decimal("0.00")
balance NUMERIC(10, 2) NOT NULL                    ← 建表语句里什么都没有
```

想和数据库结构对齐，用 `server_default`。

**记住一个坑**

**模型没被 import，等于没上户口。** 你写了 `app/models/order.py`，但没有任何地方 import 它，`Base.metadata` 里就没有这张表——建表、迁移都会漏掉它。

所以 `app/models/__init__.py` 里要把每个模型都 export 一次。

---

## 知识点 4：Session —— 取号办事，办完走人

**一句话**：Session 是办事窗口，一次业务用一个，办完就关。

**打个比方**

去银行办事：

1. 取号（`Session(engine)`）
2. 办事（查、改、提交）
3. 走人（`session.close()`）

你不会在银行一直待着不走——那别人就进不来了。Session 也一样，用完要关，把连接还给池子。

**看代码**

```python
with Session(engine) as session:      # 取号，自动处理关闭
    user = session.get(User, 1)
    print(user.username)
# 出了 with，自动 close，连接还回池子
```

`with` 的意思是：不管中间成功还是报错，出来都帮你关掉。不用自己写 `try/finally`。

**记住一个坑**

**Session 不能跨线程共用。** 一个线程一个 Session，或者一个请求一个 Session。共享会出现很难查的数据错乱。

---

## 知识点 5：查第一条数据 —— 报个身份证号

**一句话**：`session.get(User, 1)` 就是"报 id，直接调档"。

**打个比方**

你去档案馆说"我要 1 号档案"，管理员直接去那个位置拿给你。不用翻遍所有柜子。

**看时序**

```plain
   session.get(User, 1)
        │
        ▼
   生成 SQL：SELECT ... FROM users WHERE id = 1     ← 只有这时候碰数据库
        │
        ▼
   返回一个 User 对象
   （数据被"翻译"成对象：列名变成属性名）
```

**看代码**

```python
with Session(engine) as session:
    user = session.get(User, 1)
    print(user)              # <User id=1 username='张三' balance=888.00>
    print(user.username)     # 张三
    print(user.balance)      # 888.00
```

真实运行结果：

```plain
【1】按主键查一条
    返回值类型： User
    对象本身   ： <User id=1 username='张三' balance=888.00>
    取属性     ： 张三 | 888.00 | 13800000001

【2】查不到时返回什么
    session.get(User, 999999) -> None
    没有抛异常，只是 None
```

**记住一个坑**

**查不到返回 `None`，不报错。** 所以判断"用户不存在"就是 `if user is None`，不用 try/except。

---

## 知识点 6：脏检查 —— 改草稿，提交才存档

**一句话**：改属性只是在草稿上改，`commit()` 才存档；而且只存改过的那一段。

**打个比方**

你在 Word 里改文档：

- 打字的时候，文件还是原来的，**没保存就不算数**；
- 按 Ctrl+S 保存时，Word 只把**改过的段落**写进文件，不会把整篇重写一遍。

SQLAlchemy 干的是同一件事。

**看时序**

```plain
   user.balance = 100
        │
        ▼
   ① 只在内存里改，标记"这个对象脏了"        ← 此刻一条 SQL 都没发
        │
        ▼
   session.commit()
        │
        ▼
   ② 拿现在的值和"加载时的快照"逐个比对
        │
        ├── 没变 → 跳过，不发 SQL
        └── 变了 → UPDATE，只带变化的那一列
```

真实运行结果（案例 3 用事件监听抓的 SQL）：

```plain
--- ② 赋一个相同的值，然后 flush ---
    session.dirty = IdentitySet([<User object at 0x...>])   ← 对象进去了
    实际发出去的 SQL：（没有 UPDATE）

--- ③ 赋一个不同的值，然后 flush ---
    SQL: UPDATE users SET balance=%(balance)s WHERE users.id = %(users_id)s
    结论：只 UPDATE 变化的那一列，不是整行覆盖
```

两个反直觉的结论：

1. 赋**相同**的值，对象进了 dirty 集合，但**不发 UPDATE**——因为值没变；
2. UPDATE **只带变的那一列**，不是整行覆盖。

**记住一个坑**

**别在循环里 `commit()`。** 每次 commit 都是一次网络往返。批量写 100 条，正确写法是 `add_all` 之后 commit 一次（第四章测过，差 12.9 倍）。

跑一遍：`python chapters/ch03/code/03_dirty_check.py`

---

## 面试常问的 3 个问题

### 1. Engine 和 Session 有什么区别？

> **一句话**：Engine 管连接，Session 管事务和对象。
>
> **展开**：
> 1. 生命周期不同——Engine 是全局的，程序启动建一次；Session 是每次操作用的，用完就关；
> 2. 职责不同——Engine 内部持有连接池，管"怎么连数据库"；Session 是工作单元，管"这次改了什么、要不要提交"；
> 3. 线程安全不同——Engine 可以共享，Session 不行，必须一个线程一个。
>
> **加分项**：Session 不是一直占着连接，它只在执行 SQL 时才向 Engine 借，用完立刻还。

### 2. 什么是"脏检查"？什么时候才发 UPDATE？

> **一句话**：改属性只打标记，commit 时才对比快照决定发不发 SQL。
>
> **展开**：
> 1. 对象从库里查出来时，SQLAlchemy 存了一份属性快照；
> 2. 你改属性，对象进入 dirty 集合，但此刻没有任何 SQL；
> 3. commit 时逐字段对比，没变就跳过，变了就发 UPDATE，且只带变化的列。
>
> **加分项**：实测过，赋相同的值确实不会发 UPDATE；因为只更新变化列，多人改同一行的不同字段不会互相覆盖。

### 3. 什么时候用 ORM，什么时候写原生 SQL？

> **一句话**：常规增删改查用 ORM，复杂分析和批量导入用原生 SQL。
>
> **展开**：
> - 用 ORM：单表操作、简单关联、需要事务管理的业务逻辑；
> - 用原生 SQL：多表聚合报表、窗口函数、深层子查询、百万级导入。
>
> **加分项**：两者可以共存，`session.execute(text("..."))` 就能执行原生 SQL，还带参数绑定。

---

## 这一章只要记住三句话

1. **Engine 建一次，Session 建很多次**
2. **模型是类，列用 `mapped_column`，`Mapped[T]` 管类型**
3. **改属性不发 SQL，commit 才发，而且只发变化的列**

---

## 练习顺序

```bash
cd D:/github_repository/mysql-learning
export MYSQL_PASSWORD=你的密码

python chapters/ch03/code/01_first_query.py        # 四件套 + 查第一条
python chapters/ch03/code/02_pymysql_vs_orm.py     # 字典 vs 对象
python chapters/ch03/code/03_dirty_check.py        # 脏检查实测
python chapters/ch03/code/04_use_app_model.py      # 工程版对照
```

---

## 学完可以自问三句

- `add` 之后为什么 `user.id` 是 `None`？（第三章末尾讲过，第四章会用）
- `session.get()` 查不到时返回什么？
- 为什么改了属性没发 SQL？

---

## 速查卡（忘了就翻这一页）

**四件套骨架**

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engine = create_engine(url, pool_pre_ping=True)     # 全局一个

class Base(DeclarativeBase):                        # 全局一个
    pass

class User(Base):                                   # 一张表一个
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))

with Session(engine) as session:                    # 一次操作一个
    user = session.get(User, 1)
```

**常用操作**

| 想干什么 | 写法 |
| --- | --- |
| 按主键查 | `session.get(User, 1)`（查不到返回 `None`） |
| 按条件查 | `session.execute(select(User).where(...)).scalar_one_or_none()` |
| 批量查 | `session.scalars(select(User).where(...)).all()` |
| 改字段 | `user.balance = 100` 然后 `session.commit()` |
| 撤销 | `session.rollback()` |

**类型对照（最常用的五个）**

| Python | SQLAlchemy | MySQL |
| --- | --- | --- |
| `int` | `INTEGER(unsigned=True)` | `INT UNSIGNED` |
| `str` | `String(50)` | `VARCHAR(50)` |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` |
| `bool` | `TINYINT(1)` | `TINYINT(1)` |
| `datetime` | `DateTime` | `DATETIME` |

**三句话**

1. Engine 建一次，Session 建很多次
2. 模型是类，`Mapped[T]` 管类型，`mapped_column` 管列
3. 改属性不发 SQL，commit 才发

---

<small>相关：[第二章 -- Python 数据库连接池](../../ch02/notes/Python%20数据库连接池.md) · [第四章 -- 增删改查](../../ch04/notes/SQLAlchemy%20ORM%20CRUD.md)</small>
