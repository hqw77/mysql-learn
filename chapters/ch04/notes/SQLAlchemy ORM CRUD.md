# 第四章 · SQLAlchemy ORM CRUD

> **一句话**：增删改查本身不难，难的是**事务边界放哪、软删还是硬删、批量怎么不慢**。

**学习方式**：先看知识（一），再跑案例（二），然后看业务怎么用（三），跑不通查（四），最后自测（五）和总结（六）。

**分几次学**（不用一口气读完）：

| 第几次 | 干什么 | 用时 | 读到哪 |
| --- | --- | --- | --- |
| 第 1 次 | 只读知识，不写代码 | 12 分钟 | 一、1.1 ~ 1.6 |
| 第 2 次 | 跑 4 个案例 + 做「改一改」 | 20 分钟 | 二、案例 1 ~ 4 |
| 第 3 次 | 看业务场景 + 自测 3 题 | 10 分钟 | 三、五 |
| 以后 | 只翻章末速查卡 | 1 分钟 | 六、速查卡 |

---

# 一、这一章讲什么

## 1.1 add 和 commit 是两个动作

```plain
db.add(user)    → 对象进入 Session 的 new 集合，还没 SQL
db.commit()     → flush（INSERT）+ 提交事务，主键才被填上
db.refresh(u)   → 回读一次，拿到数据库生成的 created_at
```

> 💡 `add()` 之后 `user.id` 还是 `None`，这不是 bug。SQLAlchemy 不知道自增主键是多少，直到 INSERT 执行完。

> ⚠️ `commit()` 抛异常后**必须 `rollback()`**。不 rollback 的 Session 会卡在坏事务里，后面所有操作都跟着报 `PendingRollbackError`。

## 1.2 查询：`get` / `select` / 分页

| 想干什么 | 写法 |
| --- | --- |
| 按主键 | `db.get(User, 1)` |
| 按条件 | `db.execute(select(User).where(...)).scalar_one_or_none()` |
| 一批 | `db.scalars(select(User).where(...)).all()` |
| 总数 | `db.scalar(select(func.count()).select_from(User))` |

> 💡 分页让数据库做：`.offset((page-1)*size).limit(size)`。**别把整表捞回来再切片**——数据量一大就 OOM。

> ⚠️ 总数和当页条数是两回事。`len(rows)` 最多等于 `size`，拿它当总数会让前端分页器只显示一页。

## 1.3 改数据的两种写法

| 场景 | 写法 | 生成的 SQL |
| --- | --- | --- |
| 改一个对象 | `user.balance = 100; db.commit()` | `UPDATE ... WHERE id = ?`（只带变化的列） |
| 改一批 | `db.execute(update(User).where(...).values(balance=0))` | `UPDATE ... WHERE ...`（一条改 N 行） |

> 💡 改单个对象是"脏检查"在干活（第三章讲过）；批量改是 SQL 语句，不经过 ORM 的对象状态。

## 1.4 删数据：软删还是硬删

| | 软删 `is_deleted = 1` | 硬删 `DELETE` |
| --- | --- | --- |
| 数据还在吗 | 在 | 没了 |
| 能恢复吗 | 能 | 不能 |
| 关联外键 | 不会断 | 可能断 |
| 查询要多写条件吗 | 要：`WHERE is_deleted = 0` | 不要 |
| 典型场景 | 用户、订单、文章 | 日志、临时数据、合规删除 |

> ⚠️ 软删最大的坑不是删除，是**查询**。一旦加了 `is_deleted`，所有列表/详情查询都得记得过滤，漏一个有地方就会把已删数据放出来。工程上通常配一个 `active_only()` 之类的封装。

## 1.5 批量写：别在循环里 commit

| 写法 | 100 条耗时 | 原因 |
| --- | --- | --- |
| 循环 `add` + `commit` | 0.185s | 100 次网络往返 + 100 次事务提交 |
| `add_all` + 一次 `commit` | 0.014s | 1 次往返，一次提交 |

实测差 **12.9 倍**（案例 4）。

## 1.6 为什么要 service 层

第三章的 `app/routers/health.py` 里，SQL 是直接写的。这在探针接口里没问题，但业务接口不行：

| 层 | 该干什么 | 不该干什么 |
| --- | --- | --- |
| router | 收参数、返响应、状态码 | 写 SQL、开事务 |
| service | 业务规则、事务边界、抛业务异常 | 感知 HTTP |
| model | 表结构映射 | 业务判断 |

本章的工程增量就是 `app/services/user_service.py`：每个函数一个工作单元，成功 `commit`，失败 `rollback` 并把 `IntegrityError` 翻译成 `ConflictError`。

> 🔗 想验证：**案例 4**（同一套操作，直接写 vs 走 service 的差别）

---

# 二、四个可执行案例

| 案例 | 文件 | 验证什么 | 用时 |
| --- | --- | --- | --- |
| 1 | `01_add.py` | add/commit/refresh 的时序，唯一键冲突 | 4 分钟 |
| 2 | `02_query.py` | 条件、排序、分页、count | 4 分钟 |
| 3 | `03_update_delete.py` | 改的两种写法，软删 vs 硬删 | 5 分钟 |
| 4 | `04_batch_and_service.py` | 批量写入快多少，service 层长什么样 | 5 分钟 |

## 跑之前的准备

```bash
cd D:/github_repository/mysql-learning      # ⚠️ 必须从仓库根跑，脚本要 import app
export MYSQL_PASSWORD=你的密码
```

> 这四个案例都会自己清理测试数据，跑完库里还是 3 条原始用户。

---

## 案例 1 · 新增与唯一键冲突

> 🔗 对应知识点：**1.1 add 和 commit 是两个动作**

**验证什么**：`add()` 之后主键为什么是空的；重复插入在哪一步炸。

**文件**：`chapters/ch04/code/01_add.py`

**核心代码**：

```python
user = User(username=name, phone=phone, balance=0)
db.add(user)                    # 进 new 集合，没有 SQL
db.commit()                     # ← INSERT 在这里发生
db.refresh(user)                # 回读 created_at
```

**怎么跑**：

```bash
python chapters/ch04/code/01_add.py
```

**你会看到**：

```plain
--- ① 新建一个对象，add 之后还没提交 ---
    user.id = None   ← 还没 INSERT，主键是空的
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

**能学到什么**：

- `add()` ≠ `INSERT`，`commit()` 才发 SQL
- 主键和 `server_default` 的值要 `refresh()` 才回填到对象上
- 唯一键冲突只在 `commit()` 那一刻暴露，抛的是 `IntegrityError`
- 捕获后必须 `rollback()`，否则 Session 卡死

**改一改**（1 分钟）：把 `db.refresh(user)` 注释掉，再把 ③ 的打印提前到 `commit()` 之前，看 `created_at` 是 `None` 还是值。

---

## 案例 2 · 条件查询与分页

> 🔗 对应知识点：**1.2 查询：get / select / 分页**

**验证什么**：分页是不是真的让数据库做；`len()` 和 `COUNT()` 的差别。

**文件**：`chapters/ch04/code/02_query.py`

**核心代码**：

```python
stmt = select(User).order_by(User.id).offset((page-1)*size).limit(size)
rows = db.scalars(stmt).all()

total = db.scalar(select(func.count()).select_from(User))
```

**怎么跑**：

```bash
python chapters/ch04/code/02_query.py
```

**你会看到**：

```plain
--- ① 总共有多少条 ---
    COUNT(*) = 3

--- ② 条件查询：余额 > 200，按余额倒序 ---
    <User id=1 username='张三' balance=888.00>
    <User id=2 username='李四' balance=400.00>

--- ③ 分页：第 1 页，每页 2 条 ---
    SELECT ... LIMIT 2 OFFSET 0
    <User id=1 username='张三' balance=888.00>
    <User id=2 username='李四' balance=400.00>

--- ④ 第 2 页 ---
    <User id=3 username='王五' balance=100.00>

--- ⑥ count 和 len 的区别 ---
    总数（COUNT）      : 3
    当页条数（len）    : 2   ← 只是这一页，不是总数
```

**能学到什么**：

- 分页 = `LIMIT` + `OFFSET`，在数据库侧完成
- 总数必须单独 `COUNT`，不能拿 `len(rows)` 冒充
- 只取需要的列（⑤）比 `SELECT *` 省带宽，尤其是表里有大字段时

**改一改**（2 分钟）：把 `page=2` 跑一次，再改成 `page=99`（超出范围），看返回空列表而不是报错——这就是前端要处理"空页"的原因。

---

## 案例 3 · 改与删

> 🔗 对应知识点：**1.3 改数据的两种写法 · 1.4 软删还是硬删**

**验证什么**：改单个对象和批量改生成的 SQL 差在哪；软删之后行还在不在。

**文件**：`chapters/ch04/code/03_update_delete.py`

**核心代码**：

```python
target.balance = Decimal("888.00")        # 改对象
db.commit()                               # → UPDATE ... WHERE id = ?

db.execute(update(User).where(...).values(balance=0))   # 批量
db.commit()                               # → UPDATE ... WHERE ...
```

**怎么跑**：

```bash
python chapters/ch04/code/03_update_delete.py
```

**你会看到**：

```plain
--- ② 改单个对象：只改属性，commit 时发 UPDATE ---
    SQL: UPDATE users SET balance=%(balance)s WHERE users.id = %(users_id)s
    → 只改了 balance 一列

--- ③ 批量改：一条 SQL 改一批 ---
    SQL: UPDATE users SET balance=%(balance)s WHERE users.username LIKE %(username_1)s
    影响行数: 3

--- ④ 软删除：行还在，只是标记 ---
    is_deleted = 1，行仍然存在：<User id=7 username='up89884_1' balance=0>

--- ⑤ 硬删除：真的没了 ---
    再查: None   ← None
```

**能学到什么**：

- 改对象走脏检查，SQL 只带变化列；批量改走 `update()` 语句，一条 SQL 改 N 行
- `result.rowcount` 告诉你影响了几行——做"更新失败"判断很有用
- 软删只是置标记，行还在；**查询必须自己加 `is_deleted = 0`**
- 硬删之后 `db.get()` 返回 `None`

**改一改**（2 分钟）：在 ④ 之后加一句 `select(User).where(User.is_deleted == 0)`，看软删掉的那条是不是从结果里消失了——这就是"业务查询要过滤"的意思。

---

## 案例 4 · 批量写入与 service 层

> 🔗 对应知识点：**1.5 批量写 · 1.6 为什么要 service 层**

**验证什么**：批量写到底快多少；封装进 service 后调用方长什么样。

**文件**：`chapters/ch04/code/04_batch_and_service.py`

**核心代码**：

```python
db.add_all([User(...) for i in range(100)])
db.commit()                    # 一次往返

# service 层：调用方只写一行
user = user_service.create_user(db, "name", "138...", Decimal("50"))
```

**怎么跑**：

```bash
python chapters/ch04/code/04_batch_and_service.py
```

**你会看到**：

```plain
--- ① 逐条 commit：100 条 ---
--- ② add_all + 一次 commit：100 条 ---
    逐条 commit :  0.185s
    批量 commit :  0.014s
    快 12.9 倍

--- ③ 换成 service 层，调用方只写一行 ---
    创建: <User id=209 username='bt89888_svc' balance=50.00>
    改余额: 200.00 （50 + 150）
    分页: 共 204 条，本页 3 条

--- ④ service 把数据库异常翻译成了业务异常 ---
    ConflictError: 用户名或手机号已存在：bt89888_svc  → 路由层会转成 409
    NotFoundError: 用户 99999999 不存在  → 路由层会转成 404
```

**能学到什么**：

- 逐条 `commit` 是 N 次事务，批量是 1 次，差距随行数线性放大
- service 层把 `IntegrityError` 翻译成 `ConflictError`，路由层不用认识数据库异常
- `get_user` 查不到直接抛 `NotFoundError`，调用方不用写 `if user is None`

**改一改**（2 分钟）：把 `ROWS` 从 100 改成 500 再跑一次，算一下倍数变了没有——如果倍数基本不变，说明瓶颈确实在"每次 commit 的往返"。

---

# 三、业务场景对话

**Q：加了软删除，所有查询都要写 `is_deleted = 0`，漏了怎么办？**

工程上有三种做法，按靠谱程度排：

1. **在 service 层统一入口**：不让路由直接拼 `select`，所有查询都经过 `user_service`，过滤条件只写一次。
2. **封装成函数**：`def active_users(): return select(User).where(User.is_deleted == 0)`，到处复用。
3. SQLAlchemy 的 `with_loader_criteria` / 自定义 Query 类：能自动加条件，但会让"我到底查了什么"变得不透明，新手不建议。

**Q：分页翻到第 10000 页，为什么越来越慢？**

因为 `LIMIT 100000, 20` 的语义是"扫描 100020 行，扔掉前 100000 行"。页码越大，扫描越多。

三种优化，从简单到复杂：

| 做法 | 说明 |
| --- | --- |
| 限制最大页数 | 最简单，产品上通常允许（"最多看前 100 页"） |
| 游标分页 | 用 `WHERE id > last_id LIMIT 20` 代替 offset，稳定 O(1) |
| 覆盖索引 | 先查 id 再回表，减少回表次数 |

> 💡 面试里被问到"深分页怎么优化"，答**游标分页**（keyset pagination）基本就对了。

**Q：事务边界应该放在 service 还是 router？**

放 service。原因：

- 一个业务动作可能跨多个表（转账 = 扣 A + 加 B），必须在一个事务里，而 router 不该知道有几个表
- router 里开事务，会导致"调两个 service 就两个事务"，中间失败无法整体回滚
- service 内部 commit，失败 rollback 并抛业务异常，router 只管把异常映射成 HTTP 状态码

---

# 四、跑不起来怎么办

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'app'` | 没从仓库根跑 | `cd` 到仓库根再执行 |
| `Could not locate a bind configured` | `SessionLocal` 没绑 Engine | 检查 `app/db/session.py` |
| `PendingRollbackError` | 上次异常没 rollback | 在 `except` 里加 `db.rollback()` |
| `IntegrityError: Duplicate entry` | 唯一键冲突 | 捕获后转成 409，别直接抛给前端 |
| `Operand should contain 1 column(s)` | `select()` 里混了多列又当对象用 | 多列用 `db.execute(...).all()`，不要 `.scalars()` |
| 分页越翻越慢 | `OFFSET` 太大 | 改游标分页 |

---

# 五、自测：3 道面试题

### Q1. `session.add()` 和 `session.commit()` 之间发生了什么？

> **满分回答模板**
>
> 一句话：**add 只是登记，commit 才写库**。
>
> 展开：
> 1. `add()` 把对象放进 Session 的 new 集合，内存里维护，不发 SQL；
> 2. `commit()` 触发 flush：对 new 集合发 INSERT，对 dirty 集合发 UPDATE，对 deleted 集合发 DELETE；
> 3. 提交成功后主键才回填到对象上，`server_default` 生成的值还要 `refresh()` 才可见。
>
> 加分项：所以"add 了但没 commit 就退出"数据会丢；"commit 抛异常没 rollback"Session 会卡在坏事务里。

### Q2. 软删除和硬删除怎么选？

> **满分回答模板**
>
> 一句话：**能恢复、有审计、有关联的用软删，其余硬删**。
>
> 展开：
> - 软删：加 `is_deleted` 标记，行还在。用户、订单、文章这类业务数据几乎都用；
> - 硬删：`DELETE` 真删。日志、临时数据、合规要求"必须删除"的才用；
> - 代价：软删让每条查询都得带过滤条件，漏一处就会放出已删数据。
>
> 加分项：软删要配合唯一索引一起考虑——`username` 唯一的话，删掉的用户还占着这个用户名，通常要改成 `(username, is_deleted)` 联合唯一或者删除时重命名。

### Q3. 批量插入一万条，怎么最快？

> **满分回答模板**
>
> 一句话：**一次 commit，一次网络往返，必要时用 executemany**。
>
> 展开：
> - 最差：循环 `add` + `commit`，一万次事务；
> - 好一点：`add_all` + 一次 `commit`，ORM 会合并成批量 INSERT；
> - 更好：`db.execute(insert(User), [dict1, dict2, ...])` 走 executemany，绕开 ORM 的对象实例化；
> - 极致：`LOAD DATA INFILE`，适合百万级导入。
>
> 加分项：我们实测过 100 条，逐条 commit 0.185s，add_all 一次 commit 0.014s，差 12.9 倍。倍数随行数放大。

---

# 六、本章总结

**三句话**：

1. `add` 登记、`commit` 写库、`refresh` 回读
2. 软删是标记，查询得自己过滤；硬删不可恢复
3. 批量写一次 commit，业务逻辑进 service

**验收清单**：

- [ ] 能解释 `add()` 之后为什么 `id` 是 `None`
- [ ] 能说出 `len(rows)` 为什么不能当总数
- [ ] 能说出软删之后必须补的那句 `WHERE`
- [ ] 能说出事务边界为什么放 service 而不是 router

---

## 速查卡（一周后回来看这里）

**增删改查骨架**

```python
# 增
u = User(username="x", phone="138...")
db.add(u); db.commit(); db.refresh(u)

# 查
db.get(User, 1)
db.scalars(select(User).where(User.balance > 100)).all()
db.scalar(select(func.count()).select_from(User))

# 改
u.balance = 100; db.commit()                       # 单个
db.execute(update(User).where(...).values(balance=0))   # 批量

# 删
u.is_deleted = 1                                   # 软删
db.delete(u)                                       # 硬删
```

**常用片段**

| 想干什么 | 写法 |
| --- | --- |
| 分页 | `.order_by(User.id).offset((p-1)*s).limit(s)` |
| 总数 | `select(func.count()).select_from(User)` |
| 只取几列 | `db.execute(select(User.username, User.balance))` |
| 捕获冲突 | `except IntegrityError: db.rollback(); raise ConflictError` |

**三句话**

1. `add` 登记、`commit` 写库、`refresh` 回读
2. 软删是标记，查询要过滤；硬删不可恢复
3. 批量写一次 commit，事务边界在 service

**下一步**：第五章搞定关系映射——一对多、多对多，以及 `relationship` 带来的 N+1 陷阱。

---

<small>相关：[第三章 -- SQLAlchemy ORM 基础](../../ch03/notes/SQLAlchemy%20ORM%20基础.md) · [第五章 -- SQLAlchemy 进阶](../../ch05/notes/SQLAlchemy%20进阶.md)</small>
