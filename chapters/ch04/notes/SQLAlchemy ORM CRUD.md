# 第四章 · 增删改查

## 4.1 学习目标

本章在前一章的基础上,完整实现数据的增删改查,具体包括：

1. 掌握新增数据时 `add()` 与 `commit()` 的分工,理解主键与默认值的产生时机
2. 掌握按主键查询、条件查询、分页查询及总数统计
3. 掌握修改数据的两种方式（修改对象属性、批量 update 语句）及其差异
4. 理解软删除与硬删除的适用场景
5. 理解批量提交与逐条提交的性能差异
6. 理解为什么要引入 service 层,以及它如何组织事务边界

前置知识：第三章（Engine、Model、Session、脏检查）。

> **本章的读法**：正文是教材写法。每个关键概念后面有一个「通俗理解」框,正文看不懂时先看那个框。
> 本章四个案例都会自行清理测试数据,可以反复运行。

---

## 4.2 新增数据

### 4.2.1 add 与 commit 的分工

新增一条数据分为两步：

```python
user = User(username="小明", phone="13800000000")
db.add(user)      # 第一步：登记到 Session
db.commit()       # 第二步：真正写进数据库
```

| 步骤 | 方法 | 作用 | 是否发 SQL |
| --- | --- | --- | --- |
| 1 | `add()` | 把对象加入 Session 的 `new` 集合 | 否 |
| 2 | `commit()` | 执行 INSERT 并提交事务 | 是 |

> **通俗理解**：`add()` 像把商品加入购物车——车里有记录了,但还没下单,所以没有订单号。`commit()` 才是点"提交订单",这时候网站才真正生成订单,给你订单号（自增主键）,并填上下单时间。

### 4.2.2 主键与默认值的产生

`add()` 之后主键仍为 `None`,`commit()` 之后才被数据库回填；数据库中由默认值生成的字段,需要调用 `refresh()` 才能读到。

```python
user = User(username="小明", phone="138...")
db.add(user)
print(user.id)            # None

db.commit()
print(user.id)            # 1

db.refresh(user)          # 回读一次
print(user.created_at)    # 数据库填的时间
```

> **通俗理解**：主键是数据库分配的,你不提交,数据库根本不知道你要插入,自然不会给你编号。`created_at` 同理——要等数据库写完,再读回来才看得到。

### 4.2.3 唯一键冲突的处理

当插入的数据违反唯一约束（如用户名重复）时,错误在 `commit()` 阶段抛出：

```python
try:
    db.commit()
except IntegrityError:
    db.rollback()                     # 必须回滚
    raise ConflictError("用户名已存在")
```

**注意**：捕获异常后必须 `rollback()`。不回滚的 Session 会停留在坏事务中,后续所有操作都会失败。

### 4.2.4 示例与运行结果

示例文件：`chapters/ch04/code/01_add.py`

```plain
--- ① 新建一个对象,add 之后还没提交 ---
    user.id = None   ← 还没 INSERT,主键是空的
    session.new 里有它吗: 1 个  ← add 之后才进 new 集合

--- ② commit 之后 ---
    user.id = 211

--- ③ refresh 才能看到数据库填的默认值 ---
    created_at = 2026-11-04 18:58:13   ← server_default 填的
    balance    = 0   ← DEFAULT 0.00 生效

--- ④ 再插一个同名用户会怎样 ---
    捕获 IntegrityError: (1062, "Duplicate entry 'u9893646' for key 'users.username'" ...
    → 业务层要把它翻译成 409
```

---

## 4.3 查询数据

### 4.3.1 按主键查询

```python
user = db.get(User, 1)      # 查不到返回 None
```

### 4.3.2 条件查询

```python
from sqlalchemy import select

users = db.scalars(
    select(User).where(User.balance > 200).order_by(User.balance.desc())
).all()
```

### 4.3.3 分页查询

分页通过 `offset` 与 `limit` 实现,由数据库完成,不应把全部数据取回后再切片：

```python
page, size = 2, 20
stmt = (
    select(User)
    .order_by(User.id)
    .offset((page - 1) * size)      # 跳过前面的记录
    .limit(size)                     # 最多取多少条
)
rows = db.scalars(stmt).all()
```

> **通俗理解**：一本书一千页,你不会一次把全部搬到桌上,你说"给我第 2 页,每页 20 行"。`offset` 是跳过多少条,`limit` 是取多少条,都交给数据库做。

### 4.3.4 总数统计

分页接口还需要返回总条数,必须单独查询：

```python
total = db.scalar(select(func.count()).select_from(User))
```

**注意**：不能用 `len(rows)` 代替总数。`len(rows)` 最多等于 `size`,只是当前页的条数。

> **通俗理解**：`len(rows)` 数的是"这一页有几条",前端分页器要的是"一共多少条"。两者用途不同,不能互相顶替。

### 4.3.5 示例与运行结果

示例文件：`chapters/ch04/code/02_query.py`

```plain
--- ① 总共有多少条 ---
    COUNT(*) = 3

--- ② 条件查询：余额 > 200,按余额倒序 ---
    <User id=1 username='张三' balance=888.00>
    <User id=2 username='李四' balance=400.00>

--- ③ 分页：第 1 页,每页 2 条 ---
    SELECT ... LIMIT 2 OFFSET 0
    <User id=1 username='张三' balance=888.00>
    <User id=2 username='李四' balance=400.00>

--- ④ 第 2 页 ---
    <User id=3 username='王五' balance=100.00>

--- ⑥ count 和 len 的区别 ---
    总数（COUNT）      : 3
    当页条数（len）    : 2   ← 只是这一页,不是总数
```

---

## 4.4 修改数据

### 4.4.1 修改单个对象

通过修改属性完成,依赖第三章讲过的脏检查机制：

```python
user = db.get(User, 1)
user.balance = Decimal("100.00")
db.commit()        # 生成 UPDATE ... WHERE id = 1
```

生成的 SQL 只包含被修改的列。

### 4.4.2 批量修改

需要一次修改多行时,使用 `update()` 语句,一条 SQL 改一批：

```python
from sqlalchemy import update

result = db.execute(
    update(User).where(User.status == 0).values(status=1)
)
db.commit()
print(result.rowcount)      # 影响的行数
```

### 4.4.3 两种方式对比

| | 修改对象属性 | `update()` 语句 |
| --- | --- | --- |
| 适用场景 | 改已知的一两条 | 按条件批量改 |
| 生成 SQL | `UPDATE ... WHERE id = ?` | `UPDATE ... WHERE 条件` |
| 是否经过 ORM 对象 | 是 | 否 |
| 能否拿到影响行数 | 否 | 是（`rowcount`） |

> **通俗理解**：改一个对象像改自己的草稿,改哪儿算哪儿；批量改像拿个章"啪啪啪"盖一百份,一条语句解决。前者要先把数据读出来,后者直接操作数据库。

**注意**：修改对象属性时,生成的是固定值 UPDATE（`SET balance = 588`）,并发场景下存在丢更新风险,详见第五章 5.6 节。

### 4.4.4 示例与运行结果

示例文件：`chapters/ch04/code/03_update_delete.py`

```plain
--- ② 改单个对象：只改属性,commit 时发 UPDATE ---
    SQL: UPDATE users SET balance=%(balance)s WHERE users.id = %(users_id)s
    → 只改了 balance 一列

--- ③ 批量改：一条 SQL 改一批 ---
    SQL: UPDATE users SET balance=%(balance)s WHERE users.username LIKE %(username_1)s
    影响行数: 3
```

---

## 4.5 删除数据

### 4.5.1 软删除

不真正删除记录,只修改标记字段：

```python
user.is_deleted = 1
db.commit()          # 行还在,只是标记变了
```

查询时需要过滤：

```python
select(User).where(User.is_deleted == 0)
```

### 4.5.2 硬删除

真正删除记录：

```python
db.delete(user)
db.commit()          # 行没了,不可恢复
```

### 4.5.3 选型建议

| | 软删除 | 硬删除 |
| --- | --- | --- |
| 数据是否保留 | 保留 | 删除 |
| 能否恢复 | 能 | 不能 |
| 关联数据是否受影响 | 不受影响 | 可能断链 |
| 查询是否需额外条件 | 需要 | 不需要 |
| 适用场景 | 用户、订单、文章 | 日志、临时数据、合规删除 |

> **通俗理解**：软删除像把文件放进回收站,文件还在硬盘上,只是打了标记；硬删除像 Shift + Delete,彻底没了。业务数据几乎都用软删除。

**注意**：软删除的难点不在删除,而在查询。一旦引入 `is_deleted`,所有列表查询都必须带上过滤条件,漏一处就会把已删除数据返回。工程上应把该条件统一写在 service 层。

### 4.5.4 示例与运行结果

沿用 `chapters/ch04/code/03_update_delete.py`：

```plain
--- ④ 软删除：行还在,只是标记 ---
    is_deleted = 1,行仍然存在：<User id=7 username='up89884_1' balance=0>
    业务查询要自己过滤：WHERE is_deleted = 0

--- ⑤ 硬删除：真的没了 ---
    再查: None   ← None
```

---

## 4.6 批量操作性能

### 4.6.1 逐条提交

```python
for i in range(100):
    db.add(User(username=f"u{i}", ...))
    db.commit()          # 每条一次事务、一次网络往返
```

### 4.6.2 批量提交

```python
db.add_all([User(username=f"u{i}", ...) for i in range(100)])
db.commit()              # 一次事务
```

### 4.6.3 实测对比

示例文件：`chapters/ch04/code/04_batch_and_service.py`

```plain
--- ① 逐条 commit：100 条 ---
--- ② add_all + 一次 commit：100 条 ---
    逐条 commit :  0.185s
    批量 commit :  0.014s
    快 12.9 倍
```

> **通俗理解**：寄 100 个包裹,笨办法是一个个跑邮局,聪明办法是全部打包一次寄走。每次 `commit()` 就是跑一趟邮局,网络往返和事务提交的开销都省不掉。

---

## 4.7 业务分层

### 4.7.1 为什么需要 service 层

如果每个接口自己写数据库操作,会出现三个问题：

| 问题 | 后果 |
| --- | --- |
| 逻辑重复 | 新增用户时的"冲突检查 + 回滚"要在多处重复 |
| 职责混乱 | 路由层既处理 HTTP 又处理事务,难以复用 |
| 难以测试 | 不启动 Web 服务就无法测试业务逻辑 |

### 4.7.2 分层实现

把数据库操作封装到 `app/services/user_service.py`：

```python
def create_user(db: Session, username: str, phone: str) -> User:
    user = User(username=username, phone=phone)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f"用户名或手机号已存在：{username}")
    db.refresh(user)
    return user
```

路由层只负责调用：

```python
@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, payload.username, payload.phone)
```

分层后的职责：

| 层 | 负责 | 不负责 |
| --- | --- | --- |
| `routers/` | 接收请求、返回响应、状态码 | 写 SQL、开事务 |
| `services/` | 业务规则、事务边界、异常翻译 | 处理 HTTP |
| `models/` | 表结构映射 | 业务判断 |

> **通俗理解**：餐厅里前厅只管点单上菜,后厨只管做菜。如果让服务员自己炒菜,两三个客人还行,店一大就乱套了。分层之后,第六章加接口时 `user_service` 一行都不用改。

### 4.7.3 示例与运行结果

沿用 `chapters/ch04/code/04_batch_and_service.py`：

```plain
--- ③ 换成 service 层,调用方只写一行 ---
    创建: <User id=209 username='bt89888_svc' balance=50.00>
    改余额: 200.00 （50 + 150）
    分页: 共 204 条,本页 3 条

--- ④ service 把数据库异常翻译成了业务异常 ---
    ConflictError: 用户名或手机号已存在：bt89888_svc  → 路由层会转成 409
    NotFoundError: 用户 99999999 不存在  → 路由层会转成 404
```

---

## 4.8 常见错误

| 错误信息 | 原因 | 解决方法 |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'app'` | 未在仓库根目录执行 | `cd` 到仓库根目录再运行 |
| `IntegrityError: Duplicate entry` | 唯一键冲突 | 捕获后 `rollback()` 并转为业务异常 |
| `PendingRollbackError` | 上次异常未回滚 | 在 `except` 中补 `db.rollback()` |
| 分页页数越多越慢 | `OFFSET` 过大 | 改用游标分页（`WHERE id > last_id`） |
| 接口返回了已删除的数据 | 软删除后未加过滤条件 | 查询统一加 `is_deleted = 0` |
| 批量插入很慢 | 循环内 `commit()` | 改用 `add_all` + 一次 `commit` |

---

## 4.9 本章小结

1. `add()` 只登记到 Session,`commit()` 才执行 INSERT；主键与默认值在提交后才可见（默认值需 `refresh`）。
2. 分页由数据库完成（`offset` + `limit`）,总数必须单独 `COUNT`,不能用 `len()` 代替。
3. 修改单个对象依赖脏检查,只更新变化的列；批量修改用 `update()` 语句,可通过 `rowcount` 判断影响行数。
4. 业务数据用软删除,需在查询侧统一过滤；硬删除不可恢复。
5. 批量写入应合并为一次提交,实测 100 条数据相差 12.9 倍。
6. 业务逻辑应放进 service 层,统一管理事务边界与异常翻译。

---

## 4.10 练习

1. 为 `users` 表实现"按用户名模糊查询 + 分页"的 service 方法,要求同时返回总条数。
2. 写一个函数 `transfer(db, from_id, to_id, amount)`,完成两个用户之间的转账,要求任一步失败时整体回滚。
3. 运行案例 4,把 `ROWS` 改为 500,观察倍数是否变化,并解释原因。
4. 思考：如果 `username` 是唯一索引,软删除后该用户名能否被再次注册？应如何设计？

---

<small>相关：[第三章 -- SQLAlchemy ORM 基础](../../ch03/notes/SQLAlchemy%20ORM%20基础.md) · [第五章 -- SQLAlchemy 关系映射](../../ch05/notes/SQLAlchemy%20进阶.md)</small>
