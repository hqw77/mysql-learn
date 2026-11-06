# 第五章 · SQLAlchemy 关系映射

## 5.1 学习目标

本章讲解 SQLAlchemy 的关系映射（Relationship Mapping）机制，具体包括：

1. 理解一对多、多对多两种关系类型及其数据库表示方法
2. 掌握 `relationship()` 的定义方法，以及在缺少物理外键时的处理方式
3. 理解加载策略对 SQL 执行次数的影响，掌握 N+1 问题的识别与解决
4. 理解并发场景下"丢更新"现象的成因，掌握三种常用解决方案
5. 能够独立完成 `User`、`Order`、`Role` 三个模型之间的关联配置

前置知识：第三章（模型定义、Session）、第四章（增删改查、事务）。

---

## 5.2 关系映射基础

### 5.2.1 概念

关系映射是指在 ORM 模型中声明两张表之间的关联关系，使开发者可以通过对象属性直接访问关联数据，而不必手写 `JOIN` 语句。

定义关系映射之后：

```python
user.orders        # 直接取得该用户的所有订单对象
order.user         # 直接取得该订单所属的用户对象
```

上述两种访问方式，不需要显式执行 SQL，ORM 会自动生成相应的查询语句。

### 5.2.2 三种关系类型

| 关系类型 | 定义 | 数据库表示 | 示例 |
| --- | --- | --- | --- |
| 一对多 | A 的一个实例对应 B 的多个实例 | 在 B 表中存储 A 的主键 | 一个用户有多张订单 |
| 多对多 | A 的多个实例对应 B 的多个实例 | 建立独立的关联表（中间表） | 一个用户有多个角色 |
| 一对一 | A 的一个实例对应 B 的一个实例 | 在任一方存储另一方主键，并加唯一约束 | 一个用户一份详细资料 |

本章实现前两种。一对一可视为一对多的特例（设置 `uselist=False`），不再单独讨论。

### 5.2.3 本章使用的数据表

| 表名 | 说明 | 本章是否新建 |
| --- | --- | --- |
| `users` | 用户表 | 否（第三章已建） |
| `orders` | 订单表 | 否（第一章已建） |
| `roles` | 角色表 | 是（迁移 `0002`） |
| `user_roles` | 用户-角色关联表 | 是（迁移 `0002`） |

`roles` 与 `user_roles` 由 Alembic 迁移创建：

```bash
alembic upgrade head
alembic current          # 输出 0002_roles (head)
```

---

## 5.3 一对多关系

### 5.3.1 数据模型

`users` 与 `orders` 是一对多关系：一个用户可拥有多张订单，一张订单只属于一个用户。

关联字段为 `orders.user_id`，指向 `users.id`。

需要注意：本书所用的数据库中，`orders.user_id` **没有建立物理外键约束**。这是第一章讨论过的设计规范——互联网项目通常不依赖数据库外键来保证引用完整性，以避免锁竞争和分库分表的困难。

### 5.3.2 定义方法

在"一"的一方（`User`）定义集合属性，在"多"的一方（`Order`）定义单个对象属性，两者通过 `back_populates` 相互引用。

```python
# app/models/user.py
orders: Mapped[list["Order"]] = relationship(
    back_populates="user",
    order_by="Order.id",
    primaryjoin="foreign(Order.user_id) == User.id",
)

# app/models/order.py
user: Mapped["User"] = relationship(
    primaryjoin="foreign(Order.user_id) == User.id",
    back_populates="orders",
)
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| `back_populates` | 指定对方的属性名，建立双向引用 |
| `primaryjoin` | 显式声明连接条件 |
| `order_by` | 指定加载关联对象时的排序字段 |

### 5.3.3 关于 primaryjoin

`relationship()` 默认依据外键约束推断连接条件。当数据库中没有物理外键时，推断会失败，抛出如下异常：

```plain
sqlalchemy.exc.NoForeignKeysError:
Could not determine join condition between parent/child tables on relationship User.orders
- there are no foreign keys linking these tables.
```

此时必须使用 `primaryjoin` 显式指定连接条件，并用 `foreign()` 标记外键所在的一侧。

`foreign()` 的作用是告诉 SQLAlchemy："`Order.user_id` 是外键，而不是 `User.id`"。缺少该标记时，ORM 无法判断连接方向。

**注意：`primaryjoin` 必须在关系两端都声明。** 只在一端声明时，另一端仍会因推断失败而报错。这是本章最常见的配置错误。

### 5.3.4 示例与运行结果

示例文件：`chapters/ch05/code/01_relationship.py`

```python
# 查询用户
user = db.get(User, 1)

# 访问关联属性
for order in user.orders:
    print(order)
```

运行结果：

```plain
--- ① 先查用户（此时不会碰 orders 表） ---
    user: <User id=1 username='张三' balance=888.00>

--- ② 访问 user.orders —— 懒加载这时候才发 SQL ---
    订单数: 2
    <Order id=1 no='ORD001' amount=398.00>
    <Order id=2 no='ORD002' amount=1200.00>

--- ③ 反向走：从订单找到用户 ---
    order: <Order id=1 no='ORD001' amount=398.00>
    它的用户: 张三
```

### 5.3.5 使用说明

**（1）通过关系添加关联对象**

不必手动设置外键字段，ORM 会自动填充：

```python
new_order = Order(order_no="ORD900", total_amount=88)
user.orders.append(new_order)      # 自动设置 new_order.user_id = user.id
db.commit()
```

运行结果：

```plain
--- ⑤ 给某个用户加一张订单（走关系，不用手写 user_id） ---
    新增订单: <Order id=5 no='ORD900' amount=88>
    用户现在的订单数: 3
    它的 user_id 被自动设成: 1
```

**（2）使用 JOIN 进行显式查询**

关系映射并不妨碍手写关联查询。需要一次性取出多个表的字段时，显式 `join` 更合适：

```python
rows = db.execute(
    select(User.username, Order.order_no, Order.total_amount)
    .join(Order, Order.user_id == User.id)
    .order_by(Order.id)
).all()
```

运行结果：

```plain
    张三     ORD001   398.00
    张三     ORD002   1200.00
    李四     ORD003   299.00
```

注意 `join` 的连接条件仍需手动书写，原因同 5.3.3——没有物理外键可供推断。

---

## 5.4 多对多关系

### 5.4.1 数据模型

`users` 与 `roles` 是多对多关系：一个用户可有多个角色，一个角色也可属于多个用户。

多对多无法用两个表直接表示，必须引入第三张表（关联表）存储双方的对应关系。

### 5.4.2 关联表定义

```python
# app/models/role.py
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", INTEGER(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", INTEGER(unsigned=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    comment="用户-角色关联表",
)
```

设计要点：

1. 关联表只包含两个外键字段，不承担业务含义；
2. 两字段共同组成联合主键，保证同一用户与同一角色的组合不会重复；
3. 设置 `ondelete="CASCADE"`，主表记录删除时关联记录一并清除。

### 5.4.3 定义方法

两端均使用 `secondary` 参数指向关联表：

```python
# Role 侧
users: Mapped[list["User"]] = relationship(
    secondary=user_roles,
    back_populates="roles",
)

# User 侧
roles: Mapped[list["Role"]] = relationship(
    secondary="user_roles",
    back_populates="users",
)
```

`secondary` 既可以传 `Table` 对象，也可以传表名字符串。

### 5.4.4 示例与运行结果

示例文件：`chapters/ch05/code/02_many_to_many.py`

```python
user = db.get(User, 1)
admin = db.scalar(select(Role).where(Role.name == "admin"))
editor = db.scalar(select(Role).where(Role.name == "editor"))

user.roles.append(admin)
user.roles.append(editor)
db.commit()

print([r.name for r in user.roles])
```

运行结果：

```plain
--- ① 库里有哪几个角色 ---
    <Role id=1 name='admin'> - 管理员，可管理所有资源
    <Role id=2 name='editor'> - 编辑，可改内容不能删用户
    <Role id=3 name='viewer'> - 访客，只读

--- ② 给张三加两个角色 ---
    张三现在的角色: ['admin', 'editor']

--- ③ 反查：哪些用户有 admin 角色 ---
    张三

--- ④ 撤销一个角色 ---
    张三现在的角色: ['admin']

--- ⑤ 直接看中间表 ---
    user_id = 1  role_id = 1
```

从结果可见：

- 通过 `roles` 集合增删角色，关联表由 ORM 自动维护；
- 反向查询 `admin.users` 同样有效；
- 关联表可直接用 `select(user_roles)` 查看。

---

## 5.5 加载策略与 N+1 问题

### 5.5.1 延迟加载（Lazy Loading）

`relationship()` 的默认加载策略是延迟加载：查询主表时不加载关联数据，第一次访问关联属性时才发送查询。

```python
user = db.get(User, 1)     # 只查 users 表
user.orders                # 访问这一下，才查 orders 表
```

该策略适用于"关联数据可能不会被用到"的场景。缺点是在循环中反复访问时，会产生大量重复查询。

### 5.5.2 N+1 问题的产生

当查询 N 条主表记录，并在循环中逐条访问关联属性时，ORM 会为每条记录单独发送一次查询，总计 1 + N 次。

```python
users = db.scalars(select(User)).all()     # 1 次
for u in users:
    print(len(u.orders))                   # N 次
```

实测数据（3 个用户）：

```plain
--- ① 懒加载：访问 user.orders 时逐个发 SQL ---
    用户数: 3
    'from users' 的 SELECT: 1 条
    'from orders' 的 SELECT: 3 条
    合计 4 条 —— 这就是 N+1
```

N 随用户数量线性增长。若有 100 个用户，将产生 101 次查询。

### 5.5.3 解决方法

使用 `selectinload` 预先加载关联数据。ORM 会先查主表，再用 `IN` 语句一次性查出所有关联记录。

```python
from sqlalchemy.orm import selectinload

users = db.scalars(select(User).options(selectinload(User.orders))).all()
```

实测数据：

```plain
--- ② selectinload：预先加载关联，只多一条 SQL ---
    用户数: 3
    'from users' 的 SELECT: 1 条
    'from orders' 的 SELECT: 1 条
    合计 2 条 —— 与用户数无关
```

查询次数固定为 2 次，与主表记录数量无关。

### 5.5.4 三种加载策略对比

| 策略 | 写法 | SQL 次数 | 适用场景 |
| --- | --- | --- | --- |
| 延迟加载（默认） | 不额外配置 | 1 + N | 关联数据可能不用 |
| 预加载 | `options(selectinload(User.orders))` | 1 + 1 | 列表页、需要展示关联信息 |
| 连接加载 | `options(joinedload(User.orders))` | 1 | 一对一，或数据不会重复膨胀 |

`joinedload` 使用 `JOIN` 一次查完，但一对多场景下会产生重复行，数据量可能膨胀，故列表页优先使用 `selectinload`。

### 5.5.5 识别方法

开启 SQL 回显可直接观察：

```python
engine = create_engine(url, echo=True)
```

或在测试中挂载事件监听，统计语句条数：

```python
@event.listens_for(engine, "before_cursor_execute")
def _record(conn, cursor, statement, parameters, context, executemany):
    _captured.append(statement)
```

---

## 5.6 并发控制

### 5.6.1 丢更新现象

两个会话先后读取同一行记录，各自计算新值后分别提交，后提交的会覆盖先提交的结果。

示例文件：`chapters/ch05/code/04_lock.py`

```python
db1, db2 = SessionLocal(), SessionLocal()
u1 = db1.get(User, 1)      # 读到 888
u2 = db2.get(User, 1)      # 也读到 888

u1.balance = u1.balance - 300
db1.commit()               # 写入 588

u2.balance = u2.balance - 300
db2.commit()               # 写入 588，覆盖了上一次修改
```

运行结果：

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

### 5.6.2 原因分析

ORM 的"修改属性"方式生成的是固定值更新语句：

```sql
UPDATE users SET balance = 588 WHERE id = 1
```

语句中的 588 是应用层计算的结果，而非"在现有值上减 300"。因此第二次提交时，数据库无法察觉值已被他方修改。

### 5.6.3 三种解决方案

**方案一：悲观锁（Pessimistic Locking）**

读取时加行锁，使其他事务阻塞至当前事务结束。

```python
stmt = select(User).where(User.id == 1).with_for_update()
user = db.execute(stmt).scalar_one()
```

生成的 SQL：

```sql
SELECT users.id, ... FROM users WHERE users.id = :id_1 FOR UPDATE
```

代价：并发度下降，使用不当可能死锁。

**方案二：乐观锁（Optimistic Locking）**

在表中增加版本号字段，更新时校验版本。

```python
result = db.execute(
    update(User)
    .where(User.id == 1, User.version == old_version)
    .values(balance=new_balance, version=old_version + 1)
)
if result.rowcount == 0:
    raise ConflictError("数据已被他人修改，请重试")
```

代价：冲突时需要应用层重试。

**方案三：数据库原子运算**

将计算交给数据库执行。

```python
db.execute(
    update(User).where(User.id == 1).values(balance=User.balance - 300)
)
```

生成 `SET balance = balance - 300`，不存在读后覆盖的问题。代价是只能表达简单的算术运算。

### 5.6.4 选型建议

| 场景 | 推荐方案 |
| --- | --- |
| 扣减库存、扣款等简单运算 | 数据库原子运算 |
| 跨多表、需要读取后判断的业务 | 悲观锁 |
| 读多写少、希望避免锁等待 | 乐观锁 |

---

## 5.7 常见错误

| 错误信息 | 原因 | 解决方法 |
| --- | --- | --- |
| `NoForeignKeysError: Could not determine join condition` | 未声明 `primaryjoin`，或仅一端声明 | 两端都加 `primaryjoin="foreign(...) == ..."` |
| `InvalidRequestError: mapper configuration failed` | 模型未导入，关系找不到目标类 | 在 `app/models/__init__.py` 中导出 |
| `Table 'user_roles' doesn't exist` | 迁移未执行 | `alembic upgrade head` |
| 接口响应缓慢、日志显示大量查询 | N+1 | 增加 `selectinload` |
| 余额、库存数值异常偏小 | 丢更新 | 使用锁或原子运算 |

---

## 5.8 本章小结

1. 一对多在"一"方定义集合属性，在"多"方定义对象属性，通过 `back_populates` 双向绑定。
2. 多对多需要独立的关联表，两端使用 `secondary` 指定；关联表宜采用联合主键。
3. 数据库缺少物理外键时，必须用 `primaryjoin` + `foreign()` 显式声明连接条件，且两端都要写。
4. 延迟加载在循环中使用会产生 N+1 查询，列表页应改用 `selectinload`，可将查询次数从 1+N 降为 2。
5. ORM 的属性修改生成固定值 `UPDATE`，并发场景存在丢更新风险，应视情况选用悲观锁、乐观锁或原子运算。

---

## 5.9 练习

1. 为 `Order` 增加一个 `items` 关系，关联 `order_items` 表，实现"一张订单多条明细"。
2. 编写查询：统计每个用户的订单数量，要求只发送 2 条 SQL。
3. 为 `users` 表增加 `version` 字段（通过 Alembic 迁移），实现乐观锁版本的余额扣减。
4. 比较 `selectinload` 与 `joinedload` 在"一个用户 100 张订单"场景下的返回结果差异，说明原因。

---

<small>相关：[第四章 -- 增删改查](../../ch04/notes/SQLAlchemy%20ORM%20CRUD.md) · [第六章 -- FastAPI 接口](../../ch06/notes/FastAPI%20+%20MySQL.md)</small>
