# 第四章 · 增删改查（大白话版）

> 这一章不背 API。只搞清楚六件事，每件事都用一个生活里的比方讲明白。

---

## 这一章涉及哪些知识点

1. **新增数据**：`add` 和 `commit` 到底是什么关系
2. **查询数据**：查一条、查一批、分页怎么翻
3. **修改数据**：改一个和改一批，写法不一样
4. **删除数据**：软删除和硬删除，怎么选
5. **批量插入**：为什么能快 10 倍
6. **service 层**：为什么要把代码拆出去

每个知识点的讲法都一样：**一句话结论 → 打个比方 → 看代码 → 记住一个坑**。

---

## 知识点 1：新增数据 —— 先放购物车，再付款

**一句话**：`add()` 是放进购物车，`commit()` 才是付款。

**打个比方**

你在网上买东西：

| 你做的事 | 对应代码 | 发生了什么 |
| --- | --- | --- |
| 加入购物车 | `db.add(user)` | 东西在车里有记录，但还没下单，所以**没有订单号** |
| 提交订单 | `db.commit()` | 网站真正生成订单：给你订单号，写上时间和金额 |
| 刷新页面 | `db.refresh(user)` | 你才看到系统填的订单号和时间 |

所以 `add` 之后 `user.id` 是 `None`，不是代码写错了——还没下单，哪来的订单号。

**看代码**

```python
user = User(username="小明", phone="13800000000")

db.add(user)          # 放进购物车
print(user.id)        # None  ← 还没下单

db.commit()           # 付款，这时候才真正 INSERT
print(user.id)        # 1     ← 订单号出来了

db.refresh(user)      # 刷新，才能看到数据库填的 created_at
```

**记住一个坑**

`commit()` 报错之后（比如用户名重复），**一定要 `rollback()`**。

不 rollback 的话，这个"购物车"就卡在付款失败的页面上了，接下来所有操作都会跟着报错。这个坑新手最容易踩。

跑一遍：`python chapters/ch04/code/01_add.py`

---

## 知识点 2：查询 —— 让数据库帮你翻页

**一句话**：查一条用 `get`，查一批用 `select`，分页别自己切。

**打个比方**

- `db.get(User, 1)` → 你告诉图书管理员"我要 1 号书"，他直接去那个位置拿。**按键取**。
- `select(User).where(...)` → 你给管理员一个条件"所有余额大于 100 的"，他筛一遍给你。**按条件筛**。
- 分页 → 一本书一千页，你不会一次全搬到桌上，你说"给我第 2 页，每页 20 行"。**让管理员翻**。

**看代码**

```python
# 1. 按 id 查一条（查不到返回 None，不报错）
user = db.get(User, 1)

# 2. 按条件查一批
stmt = select(User).where(User.balance > 100).order_by(User.balance.desc())
users = db.scalars(stmt).all()

# 3. 分页：跳过前 20 条，取接下来 20 条（第 2 页）
stmt = select(User).order_by(User.id).offset(20).limit(20)
page2 = db.scalars(stmt).all()
```

**记住一个坑**

**总数要单独数**，不能拿 `len(users)`。

因为 `len` 数的只是"这一页有几条"，最多等于每页条数。前端的分页器要的是"一共多少条"，那个得让数据库 `COUNT(*)` 数。

```python
total = db.scalar(select(func.count()).select_from(User))   # 一共多少条
page_rows = db.scalars(stmt).all()                          # 这一页多少条
```

跑一遍：`python chapters/ch04/code/02_query.py`

---

## 知识点 3：修改 —— 改一个字 vs 盖一个章

**一句话**：改一个对象就改它的属性，改一批就用 `update()` 语句。

**打个比方**

- **改一个**：你在自己的草稿上改一个字。自然、直接。
- **改一批**：一百份文件都要盖上"已作废"的红章。你不会一份一份盖，你拿个章"啪啪啪"盖过去。

前者是 ORM 帮你盯着一个对象改；后者是发一条 SQL，让数据库一次改一堆。

**看代码**

```python
# 改一个：改属性 + commit
user = db.get(User, 1)
user.balance = Decimal("100.00")
db.commit()                      # 生成 UPDATE ... WHERE id = 1

# 改一批：一条 SQL 改 N 行
db.execute(
    update(User).where(User.status == 0).values(status=1)
)
db.commit()                      # 生成 UPDATE ... WHERE status = 0
```

**记住一个坑**

改一个对象时，SQLAlchemy 生成的是 `SET balance = 100`——写的是**你算好的那个值**。

这意味着：两个人同时读到余额 888，各自减 300，后提交的那个会把自己算的 588 写进去，前一个人的修改就没了。这叫**丢更新**。

所以扣钱、扣库存这种操作，别用"改属性"，要让数据库自己算（第五章细讲）。

跑一遍：`python chapters/ch04/code/03_update_delete.py`

---

## 知识点 4：删除 —— 回收站 vs 彻底删除

**一句话**：用户、订单这种业务数据用软删除；日志、临时数据用硬删除。

**打个比方**

- **软删除**：文件删了进回收站。文件还在硬盘上，只是打了"已删除"的标记，随时能还原。
- **硬删除**：Shift + Delete。彻底没了，找不回来。

**看代码**

```python
# 软删除：给表加一个 is_deleted 字段，置 1
user.is_deleted = 1
db.commit()              # 行还在，只是标记变了

# 硬删除：真的 DELETE
db.delete(user)
db.commit()              # 行没了
```

**记住一个坑**

软删除的坑**不在删除，在查询**。

一旦加了 `is_deleted`，你所有列表查询都得记得带上 `WHERE is_deleted = 0`。漏一个地方，删掉的用户就又冒出来了，而且很难发现。

所以这个过滤条件要写在 service 里，**只写一次**，别让每个查询各自写。

```python
# services/user_service.py
stmt = select(User).where(User.is_deleted == 0)   # 条件集中在这里
```

---

## 知识点 5：批量插入 —— 跑一百趟 vs 一次寄走

**一句话**：一百条数据，一次 `commit` 比一百次 `commit` 快一个数量级。

**打个比方**

你要寄 100 个包裹：

- **笨办法**：一个个跑邮局，填单、排队、交钱。跑 100 趟。
- **聪明办法**：全部打包，一次拉过去，一次办完。

每次 `commit()` 就是跑一趟邮局——一次网络往返、一次事务提交。跑 100 趟当然慢。

**看代码**

```python
# 慢：100 趟邮局
for i in range(100):
    db.add(User(username=f"u{i}"))
    db.commit()                        # 每次都在跑一趟

# 快：1 趟
db.add_all([User(username=f"u{i}") for i in range(100)])
db.commit()                            # 只跑一趟
```

**实测**：100 条数据，慢的 0.185 秒，快的 0.014 秒，**差 12.9 倍**。

跑一遍：`python chapters/ch04/code/04_batch_and_service.py`

---

## 知识点 6：service 层 —— 前厅和后厨

**一句话**：接口层只管"接单上菜"，真正的业务逻辑放 service，别混在一起。

**打个比方**

餐厅分三块：

| 角色 | 对应代码 | 干什么 |
| --- | --- | --- |
| 前厅服务员 | `routers/` | 迎客、点单、上菜。不需要知道菜怎么做 |
| 后厨 | `services/` | 真正做菜，管火候、管食材 |
| 仓库 | `models/` | 食材本身 |

如果让服务员自己进厨房炒菜，两三个客人还行，店一大就乱套了。

**看代码**

不用 service（接口里什么都干）：

```python
@router.post("/users")
def create_user(payload):
    user = User(username=payload.username, phone=payload.phone)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名重复")     # 接口层直接处理数据库异常
    return user
```

用 service：

```python
# routers/users.py —— 前厅只管接单
@router.post("/users")
def create_user(payload, db=Depends(get_db)):
    return user_service.create_user(db, payload.username, payload.phone)

# services/user_service.py —— 后厨负责做菜
def create_user(db, username, phone):
    user = User(username=username, phone=phone)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("用户名已存在")       # 抛业务异常，不是 HTTP 异常
    return user
```

**好处**：这段"失败要回滚、重复要报 409"的逻辑只写一次。以后写命令行工具、定时任务，也能直接调这个函数，不用管 HTTP。

> 这也是为什么第六章加接口时，`user_service` 一行都没改——它压根不知道 HTTP 的存在。

---

## 面试常问的 3 个问题

每个问题给一个「答题模板」：**一句话 → 展开两三步 → 补一句加分项**。面试时照着这个骨架说，比背定义管用。

### 1. `add()` 和 `commit()` 有什么区别？

> **一句话**：`add` 只是把对象交给 Session 管着，`commit` 才真正写进数据库。
>
> **展开**：
> 1. `add` 之后对象进入 Session 的 `new` 集合，此时没有任何 SQL 发出；
> 2. `commit` 时会 flush：对新增的发 INSERT，对修改的发 UPDATE，对删除的发 DELETE；
> 3. 提交成功后主键才回填到对象上，数据库默认值要 `refresh` 才看得到。
>
> **加分项**：所以 `add` 了不 `commit` 就退出，数据会丢；`commit` 失败不 `rollback`，Session 会卡在坏事务里。

### 2. 软删除和硬删除怎么选？

> **一句话**：能恢复、要审计、有关联数据的，用软删。
>
> **展开**：
> - 软删：加 `is_deleted` 字段做标记，行还在，随时能恢复。用户、订单、文章这类业务数据基本都用它；
> - 硬删：`DELETE` 真删，日志、临时数据、合规要求"必须删除"的才用。
>
> **加分项**：软删的代价不在删除，在查询——每条查询都得带 `is_deleted = 0`，漏一处就会把已删数据放出来，所以这个条件要统一写在 service 里。

### 3. 一次插入一万条，怎么做最快？

> **一句话**：一次 commit、一次网络往返。
>
> **展开**：
> - 最差：循环 `add` + `commit`，一万次事务；
> - 好一点：`add_all` + 一次 `commit`，ORM 会合并成批量 INSERT；
> - 更好：`db.execute(insert(User), [dict1, dict2, ...])` 走 executemany，省掉对象实例化；
> - 极致：`LOAD DATA INFILE`，适合百万级导入。
>
> **加分项**：我们实测过 100 条，逐条 commit 0.185 秒，批量 0.014 秒，差 12.9 倍，而且数据量越大差距越大。

---

## 这一章只要记住三句话

1. **`add` 是放购物车，`commit` 才是付款**
2. **软删除是打标记，查询必须自己过滤**
3. **批量写一次 commit，业务逻辑放 service**

---

## 练习顺序

```bash
cd D:/github_repository/mysql-learning
export MYSQL_PASSWORD=你的密码

python chapters/ch04/code/01_add.py                 # 新增 + 重复报错
python chapters/ch04/code/02_query.py               # 查询 + 分页
python chapters/ch04/code/03_update_delete.py       # 改 + 删
python chapters/ch04/code/04_batch_and_service.py   # 批量 + service
```

四个脚本都会自己清理测试数据，跑完库里还是原来的 3 个用户，可以放心反复跑。

---

## 学完可以自问三句

- `add` 之后 `user.id` 为什么是 `None`？
- 分页时为什么不能拿 `len(rows)` 当总数？
- 软删除之后，哪个地方最容易漏掉过滤条件？

三句都能答上来，这一章就过关了。

---

## 速查卡（忘了就翻这一页）

**增删改查骨架**

```python
# 增
u = User(username="小明", phone="13800000000")
db.add(u); db.commit(); db.refresh(u)

# 查
db.get(User, 1)                                        # 按 id 查一条
db.scalars(select(User).where(User.balance > 100)).all()   # 按条件查一批
select(User).order_by(User.id).offset(20).limit(20)    # 分页
db.scalar(select(func.count()).select_from(User))      # 总数

# 改
u.balance = 100; db.commit()                           # 改一个
db.execute(update(User).where(...).values(balance=0))  # 改一批

# 删
u.is_deleted = 1                                       # 软删
db.delete(u)                                           # 硬删
```

**四个最容易忘的点**

| 情况 | 记住这句 |
| --- | --- |
| `commit()` 报错之后 | 一定要 `db.rollback()` |
| 想看数据库填的默认值（`created_at` 等） | 先 `db.refresh(u)` |
| 分页要显示总数 | 用 `COUNT(*)`，不是 `len()` |
| 要插很多条 | `add_all` + 一次 `commit` |

**三句话**

1. `add` 是放购物车，`commit` 才是付款
2. 软删除是打标记，查询必须自己过滤
3. 批量写一次 commit，业务逻辑放 service

---

<small>相关：[第三章 -- SQLAlchemy ORM 基础](../../ch03/notes/SQLAlchemy%20ORM%20基础.md) · [第五章 -- SQLAlchemy 进阶](../../ch05/notes/SQLAlchemy%20进阶.md)</small>
