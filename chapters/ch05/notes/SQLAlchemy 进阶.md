# 第五章 · 让表之间连起来（大白话版）

> 这一章讲两件事：**怎么让两张表互相关联**，以及**关联之后冒出来的两个坑**（N+1 和抢着改数据）。

---

## 这一章涉及哪些知识点

1. **关系是什么**：一对多、多对多，分别对应生活里的什么
2. **没有物理外键怎么连**：手动指路
3. **懒加载**：用到的时候才去拿
4. **N+1 问题**：一趟一趟跑，怎么一次买齐
5. **多对多与中间表**：一张"选课表"
6. **并发丢更新**：两个人同时改同一份文件

每个知识点都是：**一句话结论 → 打个比方 → 看代码 → 记住一个坑**。

---

## 先看一张「比喻地图」

| 你要干的事 | 生活里的比方 | 对应代码 |
| --- | --- | --- |
| 一个用户对应多张订单 | 一个作者写多本书 | `relationship` 一对多 |
| 用户和角色互相拥有 | 学生选课，一张选课表 | `secondary` 多对多 |
| 没有外键怎么关联 | 门牌号没登记，只能手动指路 | `primaryjoin` + `foreign` |
| 查用户顺便拿订单 | 先买菜，要用才开冰箱 | 懒加载（默认） |
| 一次把订单也拿来 | 一次买齐，不跑第二趟 | `selectinload` |
| 两个人同时扣钱 | 抢着改同一份文件 | `with_for_update` |

## 英文词小抄

| 英文 | 中文 | 一句人话 |
| --- | --- | --- |
| `relationship` | 关系 | 告诉你两个表怎么连，能直接 `user.orders` |
| `back_populates` | 双向绑定 | 两边互相指认，A 认得 B，B 也认得 A |
| `primaryjoin` | 连接条件 | 手动写「哪个字段等于哪个字段」 |
| `foreign()` | 外键标记 | 标记哪一列是"外键"那一侧 |
| `secondary` | 中间表 | 多对多时告诉它用哪张中间表 |
| `lazy` | 懒加载 | 用的时候才查（默认行为） |
| `selectinload` | 预先加载 | 提前用一条 IN 查把关联数据都拿回来 |
| `joinedload` | 连接加载 | 用 JOIN 一次查完 |
| `N+1` | N+1 查询 | 查 1 次主表，再为每行补 1 次，一共 1+N 次 |
| `with_for_update` | 加锁读 | 读的时候把这行锁住，别人得排队 |

---

## 知识点 1：关系 —— 一个作者多本书

**一句话**：表之间的关系就三种，一对多、多对多、一对一。

**打个比方**

| 关系 | 生活例子 | 数据库怎么存 |
| --- | --- | --- |
| 一对多 | 一个作者写多本书 | 书表里存一个 `author_id` |
| 多对多 | 一个学生选多门课，一门课被多个学生选 | 单独一张"选课表" |
| 一对一 | 一个人一个身份证号 | 两边各存一个对方的 id |

这一章做前两种：`User` 有多张 `Order`（一对多），`User` 和 `Role` 互相拥有（多对多）。

**看代码**

```python
# 一对多：在"一"的那边写 orders
class User(Base):
    orders: Mapped[list["Order"]] = relationship(back_populates="user")

# 在"多"的那边写 user
class Order(Base):
    user: Mapped["User"] = relationship(back_populates="orders")
```

写好之后就能这么用：

```python
user.orders          # 这个人的所有订单
order.user           # 这张订单是谁下的
```

**记住一个坑**

两边都要写 `relationship` 并且都用 `back_populates` 指认对方。只写一边，反向就查不出来。

---

## 知识点 2：没有物理外键，怎么连 —— 手动指路

**一句话**：数据库里没建外键约束时，要手动告诉 ORM「哪两列是关联的」。

**打个比方**

正常情况下，每家每户门口都有门牌号，快递员照着门牌号就能找。

但如果小区没装门牌（数据库没建外键），快递员就懵了——他知道"订单属于某个用户"，但不知道用哪个字段对。

`primaryjoin` 就是你手写的一张纸条：**"订单的 user_id 等于用户的 id"**。

**看代码**

```python
class User(Base):
    orders: Mapped[list["Order"]] = relationship(
        back_populates="user",
        primaryjoin="foreign(Order.user_id) == User.id",   # 💡 手动指路
    )

class Order(Base):
    user: Mapped["User"] = relationship(
        primaryjoin="foreign(Order.user_id) == User.id",
        back_populates="orders",
    )
```

`foreign()` 的意思是"这一侧是外键"。

**记住一个坑**

**两边都要写 `primaryjoin`。**

只写在 `Order.user` 上，`User.orders` 仍然推断不出来，报：

```plain
NoForeignKeysError: Could not determine join condition between parent/child tables
```

这是这一章最容易卡住的地方，第一次踩必定懵。

> 顺便说一句：第一章讲过，互联网项目通常不加物理外键（避免锁竞争、方便分库分表）。所以这个"手动指路"的写法，在真实项目里很常见，不是权宜之计。

跑一遍：`python chapters/ch05/code/01_relationship.py`

---

## 知识点 3：懒加载 —— 用到才去拿

**一句话**：默认情况下，`user.orders` 不会在查用户时一起查，**你访问它的时候才查**。

**打个比方**

冰箱里有菜，但你不会一次全拿出来摆桌上。要用哪样，才去开冰箱拿哪样。

好处是不用不拿，省事；坏处是"跑一趟厨房"也是要时间的。

**看时序**

```plain
   session.get(User, 1)
        │
        ▼
   SELECT ... FROM users WHERE id = 1        ← 只查用户
        │
        ▼
   返回 User 对象
   （此时 orders 还没查，是"待查"状态）
        │
        ▼
   你访问 user.orders
        │
        ▼
   SELECT ... FROM orders WHERE user_id = 1   ← 这时候才补一条
```

**看代码 + 真实结果**

```python
user = db.get(User, 1)
print(user)            # 只有用户信息
print(user.orders)     # 访问这一下，才发 SQL 查订单
```

```plain
--- ① 先查用户（此时不会碰 orders 表） ---
    user: <User id=1 username='张三' balance=888.00>

--- ② 访问 user.orders —— 懒加载这时候才发 SQL ---
    订单数: 2
    <Order id=1 no='ORD001' amount=398.00>
    <Order id=2 no='ORD002' amount=1200.00>
```

**记住一个坑**

单次用没问题，**在循环里用就完蛋**——下一节就是讲这个。

---

## 知识点 4：N+1 —— 一趟一趟跑

**一句话**：查 1 次主表，再为每一行补 1 次关联查询，一共 1+N 次。N 是行数。

**打个比方**

你要给 3 个朋友各做一道菜：

- **笨办法**：先跑一趟超市买了个锅，然后为每道菜各跑一趟超市买食材——跑了 4 趟。
- **聪明办法**：一次性把三份食材都买回来——只跑 2 趟（一趟买锅，一趟买齐）。

3 个朋友变 100 个，笨办法就跑 101 趟。

**看时序**

```plain
懒加载：                     selectinload：
  查用户    1 条               查用户        1 条
  查订单    3 条              查订单(IN)    1 条
  ─────────────              ─────────────
  合计      4 条               合计          2 条
  （用户越多越多）             （永远 2 条）
```

**看代码**

```python
# 慢：1 + N
users = db.scalars(select(User)).all()
for u in users:
    len(u.orders)          # 每访问一次，多一条 SQL

# 快：1 + 1
users = db.scalars(select(User).options(selectinload(User.orders))).all()
```

真实运行结果：

```plain
--- ① 懒加载 ---
    用户数: 3
    'from users' 的 SELECT: 1 条
    'from orders' 的 SELECT: 3 条
    合计 4 条 —— 这就是 N+1

--- ② selectinload ---
    用户数: 3
    'from users' 的 SELECT: 1 条
    'from orders' 的 SELECT: 1 条
    合计 2 条 —— 与用户数无关
```

**记住一个坑**

**列表页一律加 `selectinload`。** 只要你在循环里访问了关系属性，八成就踩了 N+1。而且它不会报错，只会慢——最难查的那一类问题。

跑一遍：`python chapters/ch05/code/03_nplus1.py`

---

## 知识点 5：多对多 —— 一张选课表

**一句话**：多对多必须有第三张表，专门存"谁和谁有关系"。

**打个比方**

学生选课：

- 学生表存学生
- 课程表存课程
- 但"张三选了数据结构"这件事，两张表都存不下——所以单独一张**选课表**：`(学生 id, 课程 id)`

数据库里的"中间表"就是这张选课表。

**看代码**

```python
# 中间表：只有两个字段，联合主键防止重复
user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", ..., ForeignKey("users.id"), primary_key=True),
    Column("role_id", ..., ForeignKey("roles.id"), primary_key=True),
)

class Role(Base):
    users: Mapped[list["User"]] = relationship(
        secondary=user_roles,             # 💡 告诉它用哪张中间表
        back_populates="roles",
    )
```

用起来跟列表一样：

```python
user.roles.append(admin)     # 中间表自动多一行
db.commit()
user.roles.remove(editor)    # 中间表自动删一行
```

真实运行结果：

```plain
--- ② 给张三加两个角色 ---
    张三现在的角色: ['admin', 'editor']

--- ④ 撤销一个角色 ---
    张三现在的角色: ['admin']

--- ⑤ 直接看中间表 ---
    user_id = 1  role_id = 1
```

**记住一个坑**

中间表的**联合主键** `(user_id, role_id)` 不能省。省了就会出现"同一个用户绑同一个角色两次"的脏数据。

跑一遍：`python chapters/ch05/code/02_many_to_many.py`

---

## 知识点 6：并发丢更新 —— 两个人抢着改

**一句话**：两个事务读同一行、各自改、各自提交，后提交的会覆盖前一个。

**打个比方**

你和同事各下载了一份同一个文档，都改了一版，都上传覆盖。

你改的是标题，他改的是正文，结果他上传的时候，**你的标题改动没了**——因为他那份是从旧版本改的。

数据库里一模一样。

**看时序**

```plain
   会话 A              会话 B
      │                   │
   读余额 888         读余额 888        ← 两个人都拿到 888
      │                   │
   算 888-300=588         │
      │                   │
   写回 588 ✓             │
      │                算 888-300=588
      │                   │
      │                写回 588 ✓        ← 覆盖了 A 的修改
      ▼                   ▼
              最终 588，但正确应该是 288
```

真实运行结果：

```plain
--- ① 两个会话同时读到同一个余额 ---
    会话 A 读到: 888.00
    会话 B 读到: 888.00

--- ② A 先扣 300 并提交 ---
    A 提交后，库里是: 588.00

--- ③ B 也扣 300 并提交（它用的是刚才读到的旧值） ---
    B 提交后，库里是: 588.00
    正确应该是 888 - 300 - 300 = 288
    实际成了 588 —— 少了 300，这就是「丢更新」
```

**怎么解决**

| 办法 | 怎么写 | 代价 |
| --- | --- | --- |
| 加锁读 | `select(...).with_for_update()` | 别人得排队，可能死锁 |
| 乐观锁 | 加 `version` 列，`WHERE version = 旧值` | 冲突时要重试 |
| 让数据库算 | `SET balance = balance - 300` | 最省，但只能做简单运算 |

**记住一个坑**

**ORM 的"改属性"生成的是固定值**：`SET balance = 588`（你算好的结果）。所以扣钱、扣库存这种操作，光靠改属性一定会丢更新。

跑一遍：`python chapters/ch05/code/04_lock.py`

---

## 面试常问的 3 个问题

### 1. 一对多在 ORM 里怎么实现？数据库一定要有外键吗？

> **一句话**：ORM 层靠 `relationship` 和连接条件，数据库层可以没有物理外键。
>
> **展开**：
> 1. 两边都写 `relationship`，用 `back_populates` 互相指认；
> 2. 有物理外键时 SQLAlchemy 自动推断；没有时要用 `primaryjoin="foreign(子表.fk) == 父表.id"` 手动写；
> 3. 互联网项目常不加物理外键（避免锁竞争、方便分库分表），所以手动写连接条件很常见。
>
> **加分项**：两边都要写 `primaryjoin`，只写一边会报 `NoForeignKeysError`——我们踩过。

### 2. 什么是 N+1 查询？怎么解决？

> **一句话**：查 1 次主表，再为每行补 1 次关联查询，一共 1+N 次。
>
> **展开**：
> 1. 触发场景：循环里访问懒加载关系、循环里 `session.get()`、序列化时逐个访问关联属性；
> 2. 解决：`selectinload`（1+1 条，用 IN 批量查）、`joinedload`（1 条 JOIN，但可能膨胀）；
> 3. 排查：开 `echo=True` 或挂事件监听数 SQL 条数。
>
> **加分项**：实测 3 个用户，懒加载 4 条 SQL，`selectinload` 只 2 条，且用户数增加时前者线性增长、后者不变。

### 3. 并发扣减库存，怎么防止超卖？

> **一句话**：要么锁住这一行，要么让数据库原子计算。
>
> **展开**：
> 1. 先复现：两个事务读同一行，各自算，后提交的覆盖前一个；
> 2. 悲观锁：`SELECT ... FOR UPDATE`，第二个事务阻塞到第一个提交；
> 3. 乐观锁：加 `version` 列，影响行数为 0 就重试；
> 4. 原子更新：`UPDATE ... SET stock = stock - 1 WHERE stock > 0`，靠影响行数判断。
>
> **加分项**：ORM 的 `obj.field = 新值` 生成固定值 UPDATE，天然有丢更新风险，扣减类操作建议直接写原子 SQL。

---

## 这一章只要记住三句话

1. **没有物理外键，`primaryjoin` 两边都要写**
2. **懒加载 = 1 + N，列表页一律 `selectinload`**
3. **并发改同一行会丢更新，用锁或让数据库自己算**

---

## 练习顺序

```bash
cd D:/github_repository/mysql-learning
export MYSQL_PASSWORD=你的密码

python chapters/ch05/code/01_relationship.py    # 一对多 + 懒加载
python chapters/ch05/code/02_many_to_many.py    # 多对多 + 中间表
python chapters/ch05/code/03_nplus1.py          # N+1 实测（4 条 vs 2 条）
python chapters/ch05/code/04_lock.py            # 丢更新复现
```

四个脚本都会自己清理数据，跑完库还是原样。

---

## 学完可以自问三句

- 为什么 `relationship` 要写两遍 `primaryjoin`？
- 懒加载和 `selectinload` 分别发几条 SQL？
- 两个人同时扣 300，为什么最后只扣了一次？

---

## 速查卡（忘了就翻这一页）

**一对多（无物理外键）**

```python
class User(Base):
    orders: Mapped[list["Order"]] = relationship(
        back_populates="user",
        primaryjoin="foreign(Order.user_id) == User.id",
    )

class Order(Base):
    user: Mapped["User"] = relationship(
        primaryjoin="foreign(Order.user_id) == User.id",
        back_populates="orders",
    )
```

**多对多**

```python
user_roles = Table("user_roles", Base.metadata,
    Column("user_id", ..., ForeignKey("users.id"), primary_key=True),
    Column("role_id", ..., ForeignKey("roles.id"), primary_key=True),
)

class Role(Base):
    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
```

**加载策略**

| 写法 | SQL 条数 |
| --- | --- |
| 默认懒加载 | 1 + N |
| `options(selectinload(User.orders))` | 1 + 1 |
| `options(joinedload(User.orders))` | 1（可能膨胀） |

**并发三招**

```python
select(User).where(...).with_for_update()                       # 悲观锁
update(User).where(User.id == 1, User.version == v).values(...)  # 乐观锁
db.execute(text("UPDATE users SET balance = balance - 300 WHERE id = 1"))  # 原子
```

**三句话**

1. 没有物理外键，`primaryjoin` 两边都要写
2. 懒加载 = 1 + N，列表页一律 `selectinload`
3. 并发改同一行会丢更新

---

<small>相关：[第四章 -- 增删改查](../../ch04/notes/SQLAlchemy%20ORM%20CRUD.md) · [第六章 -- 做成接口](../../ch06/notes/FastAPI%20+%20MySQL.md)</small>
