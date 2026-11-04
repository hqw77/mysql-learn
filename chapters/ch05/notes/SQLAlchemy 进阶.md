# 第五章 · SQLAlchemy 进阶

> **一句话**：关系映射让「查用户」顺便拿到「他的订单」，但它带来的 N+1 和并发丢更新，才是这一章真正要解决的问题。

**学习方式**：先看知识（一），再跑案例（二），然后看业务怎么用（三），跑不通查（四），最后自测（五）和总结（六）。

**分几次学**（不用一口气读完）：

| 第几次 | 干什么 | 用时 | 读到哪 |
| --- | --- | --- | --- |
| 第 1 次 | 只读知识，不写代码 | 15 分钟 | 一、1.1 ~ 1.6 |
| 第 2 次 | 跑 4 个案例 + 做「改一改」 | 20 分钟 | 二、案例 1 ~ 4 |
| 第 3 次 | 看业务场景 + 自测 3 题 | 10 分钟 | 三、五 |
| 以后 | 只翻章末速查卡 | 1 分钟 | 六、速查卡 |

---

# 一、这一章讲什么

## 1.1 三种关系

| 关系 | 例子 | ORM 怎么写 |
| --- | --- | --- |
| 一对多 | 一个用户多张订单 | 主表 `relationship(...)`，从表 `relationship(back_populates=...)` |
| 多对多 | 用户 ↔ 角色 | 中间表 + 两边 `relationship(secondary=中间表)` |
| 一对一 | 用户 ↔ 用户详情 | 一对多 + `uselist=False` |

本章实现前两种：`User.orders`（一对多）和 `User.roles`（多对多）。

## 1.2 没有物理外键，关系映射怎么写

第一章讲过一个规范：**互联网项目通常不在数据库层加物理外键**——避免锁竞争、方便分库分表。

但 ORM 的 `relationship` 默认靠外键推断 join 条件。库里 `orders.user_id` 没有 FK 约束，直接写 `relationship` 会报：

```plain
NoForeignKeysError: Could not determine join condition between parent/child tables
```

解法是显式告诉它「哪边是外键」：

```python
orders: Mapped[list["Order"]] = relationship(
    primaryjoin="foreign(Order.user_id) == User.id",   # 💡 foreign() 标记外键那一侧
    back_populates="user",
)
```

> ⚠️ **两边都要写 `primaryjoin`**。只在一侧写，反向关系仍然推断不出来。这是本章最容易卡住的地方。

## 1.3 懒加载与 N+1

`relationship` 默认是**懒加载**：查 `User` 时不碰 `orders` 表，直到你访问 `user.orders` 才发 SQL。

好处是不用不查，坏处是列表页里每个用户都要补一条：

```python
users = db.scalars(select(User)).all()     # 1 条 SQL
for u in users:
    print(len(u.orders))                    # N 条 SQL ← 陷阱
```

三种加载策略：

| 策略 | SQL 条数 | 适用 |
| --- | --- | --- |
| `lazy="select"`（默认） | 1 + N | 关联数据不一定用到 |
| `selectinload` | 1 + 1 | **列表页首选** |
| `joinedload` | 1（JOIN） | 一对一、或数据不会重复膨胀 |

```python
from sqlalchemy.orm import selectinload
users = db.scalars(select(User).options(selectinload(User.orders))).all()
```

## 1.4 多对多与中间表

```python
user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", INTEGER(unsigned=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", INTEGER(unsigned=True), ForeignKey("roles.id"), primary_key=True),
)

class Role(Base):
    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
```

中间表用**联合主键** `(user_id, role_id)`，天然防止重复绑定。

> 💡 中间表**必须**是新表——它由 Alembic 迁移创建（本章的 `0002_roles`）。如果是给已有库加关系，先写迁移再加模型。

## 1.5 并发：丢更新

两个事务读同一行、各自计算、各自提交，后提交的会覆盖前一个：

```plain
A 读 888 → 算 588 → 提交
B 读 888（旧值）→ 算 588 → 提交     ← A 的修改没了
```

因为 ORM 生成的是 `UPDATE users SET balance = 588`，写的是「我算好的值」，不是「减 300」。

三种解法：

| 解法 | 写法 | 代价 |
| --- | --- | --- |
| 悲观锁 | `select(...).with_for_update()` | 阻塞，可能死锁 |
| 乐观锁 | 加 `version` 列，`UPDATE ... WHERE version = 旧值` | 冲突时要重试 |
| 让数据库算 | `UPDATE ... SET balance = balance - 300` | 最省，但表达力有限 |

> 🔗 想验证：**案例 4**（先复现丢更新，再看 FOR UPDATE 生成的 SQL）

## 1.6 迁移：给已有库加表

本章的角色表不是手动建的，是 Alembic 迁移建的：

```bash
alembic revision -m "add roles and user_roles"   # 手写迁移文件
alembic upgrade head                              # 执行
alembic check                                     # 确认模型与库一致
```

迁移文件里写 `op.create_table(...)`，和模型定义一一对应。改完跑 `alembic check`，输出 `No new upgrade operations detected` 才算对齐。

> ⚠️ 不要用 `create_all` 建新表——它不记录版本，下次别人拉代码不知道要建什么。

---

# 二、四个可执行案例

| 案例 | 文件 | 验证什么 | 用时 |
| --- | --- | --- | --- |
| 1 | `01_relationship.py` | 一对多：懒加载时机、双向导航 | 5 分钟 |
| 2 | `02_many_to_many.py` | 多对多：中间表自动维护 | 5 分钟 |
| 3 | `03_nplus1.py` | N+1 到底多发几条 SQL，怎么修 | 5 分钟 |
| 4 | `04_lock.py` | 丢更新的复现与三种解法 | 6 分钟 |

## 跑之前的准备

```bash
cd D:/github_repository/mysql-learning      # ⚠️ 必须从仓库根跑
export MYSQL_PASSWORD=你的密码
```

> 四个案例都会自己清理数据，跑完库还是 3 个用户、3 张订单、0 条角色关联。

---

## 案例 1 · 一对多

> 🔗 对应知识点：**1.2 没有物理外键怎么写关系**

**验证什么**：`user.orders` 什么时候发 SQL；能不能从订单反查到用户。

**文件**：`chapters/ch05/code/01_relationship.py`

**核心代码**：

```python
orders: Mapped[list["Order"]] = relationship(
    primaryjoin="foreign(Order.user_id) == User.id",
    back_populates="user",
)
```

**怎么跑**：

```bash
python chapters/ch05/code/01_relationship.py
```

**你会看到**：

```plain
--- ① 先查用户（此时不会碰 orders 表） ---
    user: <User id=1 username='张三' balance=888.00>
    这一步的 SQL: ['SELECT users... FROM users WHERE users.id = %(pk_1)s']

--- ② 访问 user.orders —— 懒加载这时候才发 SQL ---
    订单数: 2
    <Order id=1 no='ORD001' amount=398.00>
    <Order id=2 no='ORD002' amount=1200.00>

--- ③ 反向走：从订单找到用户 ---
    order: <Order id=1 no='ORD001' amount=398.00>
    它的用户: 张三

--- ⑤ 给某个用户加一张订单（走关系，不用手写 user_id） ---
    新增订单: <Order id=5 no='ORD900' amount=88>
    用户现在的订单数: 3
    它的 user_id 被自动设成: 1
```

**能学到什么**：

- 查 `User` 时**不会**查 `orders`，访问属性才查（懒加载）
- 双向都能走：`user.orders` 和 `order.user`
- `user.orders.append(order)` 会自动填 `user_id`，不用手写外键
- 没有物理外键时，`join` 条件要自己写（案例 ④）

**改一改**（2 分钟）：把 ① 里的 `db.get(User, 1)` 改成 `select(User)` 查全部，再在循环里访问 `u.orders`——SQL 条数会从 2 条变成 1 + 3 条，这就是案例 3 要讲的 N+1。

---

## 案例 2 · 多对多

> 🔗 对应知识点：**1.4 多对多与中间表**

**验证什么**：`user.roles.append(...)` 之后中间表是不是自动多了一行。

**文件**：`chapters/ch05/code/02_many_to_many.py`

**核心代码**：

```python
user.roles.append(admin)      # 中间表自动 INSERT
db.commit()
user.roles.remove(editor)     # 中间表自动 DELETE
```

**怎么跑**：

```bash
python chapters/ch05/code/02_many_to_many.py
```

**你会看到**：

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

**能学到什么**：

- 多对多的增删改都是操作 `user.roles` 这个集合，中间表由 ORM 维护
- 反向查也通：`admin.users` 拿到所有管理员
- 中间表可以用 `select(user_roles)` 直接查，方便排查
- 联合主键保证同一个用户绑同一个角色不会出现两行

**改一改**（2 分钟）：在 ② 之后把 `admin` 再加一次（`user.roles.append(admin)`），commit 看会不会报错——联合主键会挡住重复，但 ORM 层面可能只是无操作。想清楚为什么。

---

## 案例 3 · N+1

> 🔗 对应知识点：**1.3 懒加载与 N+1**

**验证什么**：懒加载和 `selectinload` 的 SQL 条数差多少。

**文件**：`chapters/ch05/code/03_nplus1.py`

**核心代码**：

```python
# 懒加载：1 + N
users = db.scalars(select(User)).all()
for u in users:
    len(u.orders)

# selectinload：1 + 1
users = db.scalars(select(User).options(selectinload(User.orders))).all()
```

**怎么跑**：

```bash
python chapters/ch05/code/03_nplus1.py
```

**你会看到**：

```plain
--- ① 懒加载：访问 user.orders 时逐个发 SQL ---
    用户数: 3
    'from users' 的 SELECT: 1 条
    'from orders' 的 SELECT: 3 条
    合计 4 条 —— 这就是 N+1

--- ② selectinload：预先加载关联，只多一条 SQL ---
    用户数: 3
    'from users' 的 SELECT: 1 条
    'from orders' 的 SELECT: 1 条
    合计 2 条 —— 与用户数无关
```

**能学到什么**：

- N+1 的 N 是"每个主表行补一条查询"，用户越多越慢
- `selectinload` 用 `IN (...)` 一次查完关联，条数固定 2 条
- 这和第 4 章"别在循环里 `session.get()`"是同一类问题，只是更隐蔽——你没写循环，`relationship` 替你写了

**改一改**（3 分钟）：把用户数从 3 改成更多（先插几条测试用户再跑），观察懒加载的 SQL 条数线性增长，而 `selectinload` 始终是 2 条。

---

## 案例 4 · 并发丢更新

> 🔗 对应知识点：**1.5 并发：丢更新**

**验证什么**：两个会话各扣 300，为什么最后只扣了一次。

**文件**：`chapters/ch05/code/04_lock.py`

**核心代码**：

```python
u1 = db1.get(User, 1)      # 888
u2 = db2.get(User, 1)      # 888（另一个会话）
u1.balance -= 300; db1.commit()     # 588
u2.balance -= 300; db2.commit()     # 588 ← 覆盖了
```

**怎么跑**：

```bash
python chapters/ch05/code/04_lock.py
```

**你会看到**：

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

--- ④ 换成加锁读：SELECT ... FOR UPDATE ---
    SELECT users.id, ... FROM users WHERE users.id = :id_1 FOR UPDATE
    → 结尾多出的 FOR UPDATE 就是加锁
```

**能学到什么**：

- ORM 的 `UPDATE` 写的是**算好的值**，不是表达式，所以并发下会互相覆盖
- `with_for_update()` 让第二个事务阻塞，读到最新值
- 三种解法各有代价：悲观锁会阻塞、乐观锁要重试、原子更新表达力有限

**改一改**（3 分钟）：把 ③ 改成 `u2.balance = u2.balance - Decimal("300.00")` 之前先 `db2.refresh(u2)`，再看结果——refresh 会重新读库，就不会丢了。想清楚这是不是能在生产用（答案：能，但有竞态窗口）。

---

# 三、业务场景对话

**Q：`selectinload` 和 `joinedload` 到底选哪个？**

看数据形状：

| 场景 | 选 | 为什么 |
| --- | --- | --- |
| 列表页，每行要显示子项（如订单数） | `selectinload` | 两条 SQL，不会因 JOIN 产生重复行 |
| 一对一（用户-详情） | `joinedload` | 一条 SQL 搞定，没有膨胀 |
| 一对多，但只取少量（如取最新 1 条） | 单独查 | 别为了省一条 SQL 把整张子表拉进内存 |

> 💡 记一个直觉：**`joinedload` 会产生笛卡尔积，`selectinload` 不会**。一对多默认用后者。

**Q：删除用户，他的订单怎么办？**

三种策略，取决于业务：

| 策略 | 写法 | 适用 |
| --- | --- | --- |
| 级联删除 | `relationship(cascade="all, delete-orphan")` | 订单没有独立价值时（如草稿） |
| 软删 | 用户 `is_deleted=1`，订单不动 | 最常用，可恢复 |
| 阻止删除 | 有订单就报错 | 财务、合规场景 |

⚠️ 物理外键上的 `ON DELETE CASCADE` 和 ORM 的 `cascade="all, delete-orphan"` 是**两回事**：前者由数据库执行，后者由 ORM 在 Session 里逐个 `DELETE`。没有物理外键时，只有后者生效。

**Q：关系映射会不会让查询变慢？**

不是关系本身慢，是**加载策略**选错才慢。

- 一对多默认懒加载：列表页 N+1
- 改成 `selectinload`：固定 2 条
- 再进一步：只查需要展示的列，不要 `select(User)` 全字段

一句话：**关系映射是写法上的便利，性能要自己盯着 SQL 条数。**

---

# 四、跑不起来怎么办

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `NoForeignKeysError: Could not determine join condition` | 没写 `primaryjoin`，或只写了一边 | 两边都加 `primaryjoin="foreign(...) == ..."` |
| `InvalidRequestError: ... mapper configuration failed` | 模型没 import，关系找不到类 | 在 `app/models/__init__.py` 里导出 |
| `Table 'user_roles' doesn't exist` | 迁移没执行 | `alembic upgrade head` |
| `CircularDependencyError` | 两边都写了 FK 且互相依赖 | 用 `use_alter=True` 或改逻辑外键 |
| 页面很慢，SQL 几百条 | N+1 | 加 `selectinload(User.orders)` |
| 余额莫名其妙少了 | 丢更新 | `with_for_update()` 或原子更新 |

---

# 五、自测：3 道面试题

### Q1. 一对多关系在 ORM 里怎么实现？数据库层需要外键吗？

> **满分回答模板**
>
> 一句话：**ORM 层用 relationship + join 条件，数据库层可以没有物理外键**。
>
> 展开：
> 1. 主表一侧 `relationship`，从表一侧 `back_populates`，两边都要能推出 join 条件；
> 2. 有物理外键时 SQLAlchemy 自动推断；没有时要用 `primaryjoin="foreign(Child.fk) == Parent.id"` 显式声明；
> 3. 互联网项目常不加物理外键（避免锁竞争、方便分库分表），所以显式 join 条件很常见。
>
> 加分项：两边都要写 `primaryjoin`，只写一边会报 `NoForeignKeysError`——我们踩过。

### Q2. 什么是 N+1 查询？怎么解决？

> **满分回答模板**
>
> 一句话：**查 1 次主表，再为每一行补 1 次关联查询，总数 1+N**。
>
> 展开：
> 1. 触发场景：循环里访问懒加载关系、循环里 `session.get()`、序列化时逐个访问关联属性；
> 2. 解决：`selectinload`（1+1 条，用 IN 批量查）、`joinedload`（1 条 JOIN，但可能膨胀）；
> 3. 排查：开 `echo=True` 或挂事件监听数 SQL 条数。
>
> 加分项：我们实测 3 个用户，懒加载发 4 条 SQL，`selectinload` 只发 2 条，而且用户数增加时前者线性增长、后者不变。

### Q3. 并发扣减库存/余额，怎么做才不超卖？

> **满分回答模板**
>
> 一句话：**要么锁住这一行，要么让数据库原子计算**。
>
> 展开：
> 1. 先复现：两个事务读同一行，各自算，后提交的覆盖前一个（丢更新）；
> 2. 悲观锁：`SELECT ... FOR UPDATE`，第二个事务阻塞到第一个提交；
> 3. 乐观锁：加 `version` 列，`UPDATE ... WHERE id=? AND version=?`，影响行数为 0 就重试；
> 4. 原子更新：`UPDATE ... SET stock = stock - 1 WHERE stock > 0`，靠影响行数判断是否成功。
>
> 加分项：ORM 的 `obj.field = new_value` 生成的是固定值 UPDATE，天然有丢更新风险，扣减类操作建议直接写原子 SQL。

---

# 六、本章总结

**三句话**：

1. 关系映射让对象能互相走，但 join 条件要写清楚（没有物理外键时尤其）
2. 懒加载 = 1 + N，列表页一律 `selectinload`
3. 并发改同一行会丢更新，用锁或原子更新

**验收清单**：

- [ ] 能说出没有物理外键时关系映射怎么配
- [ ] 能解释 N+1 是怎么产生的，以及 `selectinload` 为什么是 1+1
- [ ] 能复述丢更新的两次读写过程
- [ ] 能说出三种并发解法各自的代价

---

## 速查卡（一周后回来看这里）

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
select(User).where(...).with_for_update()      # 悲观锁
update(User).where(User.id == 1, User.version == v).values(...)  # 乐观锁
db.execute(text("UPDATE users SET balance = balance - 300 WHERE id = 1"))  # 原子
```

**三句话**

1. 没有物理外键，join 条件两边都要写
2. 懒加载 = 1 + N，列表页一律 `selectinload`
3. 并发改同一行会丢更新

**下一步**：第六章把这一套暴露成 REST API——`schemas` 校验入参、`routers` 定义接口、`services` 复用本章的逻辑。

---

<small>相关：[第四章 -- SQLAlchemy ORM CRUD](../../ch04/notes/SQLAlchemy%20ORM%20CRUD.md) · [番外01 -- Alembic 数据库迁移](../../extras/notes/01-Alembic%20数据库迁移.md)</small>
