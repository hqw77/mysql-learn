# 第六章 · FastAPI + MySQL

> **一句话**：把 ORM 包成 HTTP 接口，关键不在"能返回 JSON"，而在**谁负责校验、谁负责业务、错误怎么变成状态码**。

**学习方式**：先看知识（一），再跑案例（二），然后看业务怎么用（三），跑不通查（四），最后自测（五）和总结（六）。

**分几次学**：

| 第几次 | 干什么 | 用时 | 读到哪 |
| --- | --- | --- | --- |
| 第 1 次 | 只读知识，不写代码 | 12 分钟 | 一、1.1 ~ 1.6 |
| 第 2 次 | 跑 3 个案例 + 做「改一改」 | 18 分钟 | 二、案例 1 ~ 3 |
| 第 3 次 | 看业务场景 + 自测 3 题 | 8 分钟 | 三、五 |
| 以后 | 只翻章末速查卡 | 1 分钟 | 六、速查卡 |

---

# 一、这一章讲什么

## 1.1 三层各管一件事

```plain
HTTP 请求
   │
   ▼
┌─────────────┐  只做：收参数、返响应、定状态码
│  router     │  不做：校验格式（schema 管）、业务判断（service 管）
└──────┬──────┘
       ▼
┌─────────────┐  只做：业务规则、事务边界、抛业务异常
│  service    │  不感知 HTTP
└──────┬──────┘
       ▼
┌─────────────┐  只做：表结构映射
│  model      │
└─────────────┘
```

对应的文件：

| 层 | 文件 | 本章新增 |
| --- | --- | --- |
| schema | `app/schemas/user.py` | `UserCreate` / `UserOut` / `UserPage` |
| router | `app/routers/users.py` | 5 个接口 |
| service | `app/services/user_service.py` | 第四章已写，本章直接复用 |

> 💡 复用是关键：第六章**没有改 service**，只是给它套了层 HTTP。这说明第四章的分层是有效的。

## 1.2 schema：入参校验与响应裁剪

```python
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r"^1\d{10}$")
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)
```

校验失败时 FastAPI 自动返回 **422**，你一行 `if` 都不用写。

响应侧的关键是 `from_attributes`：

```python
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # 💡 直接吃 ORM 对象
```

于是 router 里可以 `return user`，FastAPI 自动把 ORM 对象转成 JSON。

> ⚠️ `UserOut` 决定了**哪些字段能暴露**。别偷懒直接返回 `User` 对象——那样会把 `password_hash` 之类的字段一起吐出去（本书暂时没有这个字段，但真实项目一定有）。

## 1.3 router：状态码是有语义的

| 动作 | 状态码 | 什么时候用 |
| --- | --- | --- |
| GET 成功 | 200 | 查到数据 |
| POST 成功 | **201** | 创建了新资源 |
| PUT 成功 | 200 | 修改成功，返回新对象 |
| DELETE 成功 | **204** | 删除成功，**无响应体** |
| 参数格式错 | 422 | FastAPI 自动 |
| 查不到 | 404 | 业务层抛 `NotFoundError` |
| 唯一键冲突 | 409 | 业务层抛 `ConflictError` |

## 1.4 异常怎么变成状态码

`app/core/exceptions.py` 定义业务异常，`app/main.py` 统一捕获：

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

于是 service 里直接 `raise NotFoundError("用户 1 不存在")`，HTTP 层自动得到：

```json
{"detail": "用户 1 不存在"}
```

> 💡 好处是 service 完全不知道 HTTP 的存在——它抛的是业务异常，不是 `HTTPException`。测试 service 时不需要起 Web 服务。

## 1.5 分页接口该怎么设计

```python
@router.get("", response_model=UserPage)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = user_service.list_users(db, page=page, size=size)
    return UserPage(total=total, page=page, size=size, items=items)
```

响应长这样：

```json
{"total": 3, "page": 1, "size": 2, "items": [...]}
```

三个细节：

- `le=100` 限制每页上限，防止有人 `size=999999` 拖垮数据库
- `total` 用 `COUNT(*)`，不是 `len(items)`
- 元信息和数据放在同一个对象里，前端一次拿全

## 1.6 TestClient：不起服务也能调接口

```python
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    r = client.get("/users/1")
    print(r.status_code, r.json())
```

它把请求直接打进应用，不用起 uvicorn、不用管端口。第七章的自动化测试就是用这个。

---

# 二、三个可执行案例

| 案例 | 文件 | 验证什么 | 用时 |
| --- | --- | --- | --- |
| 1 | `01_schemas.py` | 校验规则在哪挡、挡不住什么 | 4 分钟 |
| 2 | `02_api_read.py` | 读接口、404、422、接口清单 | 5 分钟 |
| 3 | `03_api_write.py` | 201/409/422/200/204 各自怎么来 | 6 分钟 |

## 跑之前的准备

```bash
cd D:/github_repository/mysql-learning      # ⚠️ 必须从仓库根跑
export MYSQL_PASSWORD=你的密码
```

> 案例 3 会自己清理测试数据。

---

## 案例 1 · Pydantic 校验

> 🔗 对应知识点：**1.2 schema：入参校验与响应裁剪**

**验证什么**：哪些错误在进业务层之前就被挡住了。

**文件**：`chapters/ch06/code/01_schemas.py`

**核心代码**：

```python
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r"^1\d{10}$")
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)
```

**怎么跑**：

```bash
python chapters/ch06/code/01_schemas.py
```

**你会看到**：

```plain
--- ① 合法数据：直接构造成功 ---
    对象: username='张三丰' phone='13800000001' balance=Decimal('100.00')

--- ② 用户名太短（min_length=2） ---
    字段 username: String should have at least 2 characters

--- ③ 手机号格式不对（pattern ^1\d{10}$） ---
    字段 phone: String should match pattern '^1\d{10}$'

--- ④ 余额为负（ge=0） ---
    字段 balance: Input should be greater than or equal to 0

--- ⑤ 不传 balance 会怎样 ---
    balance 默认值: 0.00   ← Field(default=...) 生效
```

**能学到什么**：

- 长度、格式、范围校验都是声明式的，不用写 `if`
- 错误信息自带字段名和原因，前端可以直接展示
- schema **挡不住**"用户名重复""余额不足"——那是业务规则，归 service

**改一改**（2 分钟）：把 `phone` 的 pattern 改成 `^\d{11}$`（不要求 1 开头），再跑一次，看 `12345678901` 能不能通过——体会"校验规则就是产品规则"。

---

## 案例 2 · 读接口

> 🔗 对应知识点：**1.3 router · 1.4 异常映射 · 1.5 分页**

**验证什么**：200 / 404 / 422 分别由谁产生。

**文件**：`chapters/ch06/code/02_api_read.py`

**核心代码**：

```python
r = client.get("/users", params={"page": 1, "size": 2})
r = client.get("/users/99999")      # 404，由 AppError 处理器生成
r = client.get("/users", params={"size": 999})   # 422，由 FastAPI 生成
```

**怎么跑**：

```bash
python chapters/ch06/code/02_api_read.py
```

**你会看到**：

```plain
--- ① 健康检查 ---
    状态码: 200  响应: {'status': 'ok'}

--- ② 用户列表（分页） ---
    状态码: 200
    total = 3  page = 1  size = 2
    {'id': 3, 'username': '王五', 'phone': '13800000003', 'balance': '100.00', ...}

--- ③ 用户详情 ---
    状态码: 200

--- ④ 查不存在的用户 → 404 ---
    状态码: 404
    响应: {'detail': '用户 99999 不存在'}
    ← 这行 JSON 来自 main.py 里的 AppError 处理器

--- ⑤ 参数不合法 → 422（FastAPI 自动挡） ---
    状态码: 422
    第一条错误: Input should be less than or equal to 100

--- ⑥ 打开文档看看 ---
    已注册的接口: ['/health', '/health/db', '/users', '/users/{user_id}', '/users/{user_id}/balance']
```

**能学到什么**：

- 404 的响应体是业务异常处理器生成的，不是 FastAPI 默认的
- 422 是 FastAPI 在进路由前挡下的，service 根本收不到请求
- `balance` 序列化成了字符串 `"100.00"`——`Decimal` 避免精度丢失的常规做法

**改一改**（2 分钟）：把 `/users` 的 `size` 上限从 100 改成 3，再请求 `size=5`，看 422 的错误文案怎么变。

---

## 案例 3 · 写接口

> 🔗 对应知识点：**1.3 状态码 · 1.4 异常映射**

**验证什么**：201 / 409 / 422 / 200 / 204 各自是谁产生的。

**文件**：`chapters/ch06/code/03_api_write.py`

**核心代码**：

```python
@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    return user_service.create_user(db, payload.username, payload.phone, payload.balance)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    user_service.soft_delete(db, user_id)
```

**怎么跑**：

```bash
python chapters/ch06/code/03_api_write.py
```

**你会看到**：

```plain
--- ① 创建用户 → 201 ---
    状态码: 201
    响应: {'id': 213, 'username': 'api90067', 'balance': '100.00', ...}

--- ② 再建一个同名的 → 409 ---
    状态码: 409
    响应: {'detail': '用户名或手机号已存在：api90067'}

--- ③ 入参不合法 → 422（还没进 service） ---
    状态码: 422
    username: String should have at least 2 characters

--- ④ 调整余额 → 200 ---
    状态码: 200  新余额: 150.00

--- ⑤ 删除（软删）→ 204 ---
    状态码: 204  响应体: ''

--- ⑥ 删除后：列表里消失了，但详情还在 ---
    列表里有它吗: False   ← list 过滤了 is_deleted
    详情状态码: 200  is_deleted = True
    ⚠️ 详情不过滤软删，这是产品决策，不是 bug
```

**能学到什么**：

- 201 和 204 是**显式声明**的，不是默认 200
- 409 来自 service 的 `ConflictError`，说明"唯一键冲突"被翻译成了业务语义
- 422 发生在 service 之前——请求根本没进来
- 软删之后列表查不到、详情还能查到，这是两种不同的产品选择

**改一改**（3 分钟）：把 `delete_user` 改成调用 `user_service().hard_delete`，再跑一次，看 ⑥ 的详情是不是变成 404——对比软删和硬删在接口层暴露出的差别。

---

# 三、业务场景对话

**Q：接口为什么不能直接返回 ORM 对象？**

三个原因：

| 风险 | 说明 |
| --- | --- |
| 泄露字段 | `User` 有 `password_hash` 就一起吐出去了 |
| 泄露关系 | 返回 `user.orders` 时可能触发 N+1，甚至递归 |
| 接口不稳定 | 数据库加一列，前端突然多收一个字段 |

所以要有 `UserOut` 这层"白名单"。FastAPI 的 `response_model` 会按它裁剪，多余字段自动丢弃。

**Q：业务异常该抛 `HTTPException` 还是自定义异常？**

抛自定义的（本项目的 `AppError`）。理由：

- service 不该知道 HTTP 的存在，否则没法在 CLI、定时任务里复用
- 统一在 `main.py` 映射，改状态码只改一处
- 测试 service 时不用构造 Request

只有在 router 层做"纯 HTTP 决策"（比如读 header、判断 Accept）时，才直接用 `HTTPException`。

**Q：接口文档（/docs）是自动生成的吗？**

是。FastAPI 从三处生成：

1. 路由签名 → 路径、方法、参数位置；
2. Pydantic 模型 → 请求体/响应体结构；
3. `summary` / `description` / `Field(description=...)` → 文档文字。

所以**模型写得越清楚，文档越完整**，不用额外手写 swagger。

---

# 四、跑不起来怎么办

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'app'` | 没从仓库根跑 | `cd` 到仓库根 |
| `ModuleNotFoundError: httpx` | 没装测试依赖 | `pip install httpx` |
| `422 Unprocessable Entity` | 入参不符合 schema | 看 `detail` 里哪个字段 |
| `500 Internal Server Error` | 异常没被捕获 | 看控制台 traceback；业务异常要继承 `AppError` |
| `response_model` 报字段缺失 | ORM 对象缺字段 / 名字不一致 | 用 `from_attributes=True` 并核对字段名 |
| `Decimal` 序列化成字符串 | 正常行为 | 前端按字符串处理，别直接 `parseFloat` 做金额运算 |
| 接口 404 但路径没错 | 路由没注册 | 检查 `app.include_router(...)` |

---

# 五、自测：3 道面试题

### Q1. FastAPI 里怎么管理数据库 Session？

> **满分回答模板**
>
> 一句话：**用依赖注入 + `yield`，每个请求一个 Session，请求结束自动归还**。
>
> 展开：
> 1. `get_db()` 是生成器依赖：`db = SessionLocal()`，`yield db`，`finally: db.close()`；
> 2. 路由函数参数写 `db: Session = Depends(get_db)`，FastAPI 自动注入并在响应后执行 `finally`；
> 3. Session 只在执行 SQL 时才向 Engine 借连接，用完归还，不是整个请求都占着连接。
>
> 加分项：`yield` 保证请求抛异常时也会关闭，避免连接泄漏——这和第二章"忘记 close 会卡死池子"是同一个问题。

### Q2. 接口的 400、422、409、500 分别代表什么？

> **满分回答模板**
>
> 一句话：**422 是格式错，400 是业务参数错，409 是冲突，500 是没兜住的异常**。
>
> 展开：
> - 422：Pydantic 校验失败（类型、长度、格式、范围），FastAPI 自动返回；
> - 400：格式对但业务不允许，比如"余额不足"；
> - 409：资源冲突，典型是唯一键重复（用户名已存在）；
> - 500：代码抛了没捕获的异常，属于 bug，不该出现在正常流程里。
>
> 加分项：我们的做法是 service 抛 `AppError` 子类（`NotFoundError` 404 / `ConflictError` 409），`main.py` 统一映射，router 里一个 `try` 都不写。

### Q3. 为什么要有 schema 层，直接用 ORM 模型不行吗？

> **满分回答模板**
>
> 一句话：**ORM 描述数据库，schema 描述接口，两者变更节奏不同**。
>
> 展开：
> 1. 安全：schema 是白名单，能挡住 `password_hash` 这类不该暴露的字段；
> 2. 稳定：数据库加列不会让接口响应突然多字段，前端不受影响；
> 3. 校验：`min_length`、`pattern` 这类规则属于接口契约，不该写进表结构。
>
> 加分项：我们用一个 `UserOut` 同时做响应模型和文档来源，`/docs` 里的字段说明就是从 `Field(description=...)` 自动生成的。

---

# 六、本章总结

**三句话**：

1. schema 管格式，service 管业务，router 只管 HTTP
2. 状态码有语义：201 创建、204 删除、409 冲突、422 格式
3. 业务异常在 service 抛，在 main 统一映射

**验收清单**：

- [ ] 能说出 422 和 400 的区别
- [ ] 能解释为什么 `response_model` 不能用 ORM 模型直接顶替
- [ ] 能说出 `get_db` 里 `yield` 的作用
- [ ] 能解释 204 为什么没有响应体

---

## 速查卡（一周后回来看这里）

**三层骨架**

```python
# schemas/user.py
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r"^1\d{10}$")

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; username: str; balance: Decimal

# routers/users.py
@router.get("", response_model=UserPage)
def list_users(page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    items, total = user_service.list_users(db, page=page, size=10)
    return UserPage(total=total, page=page, size=10, items=items)

# main.py
app.include_router(users.router)
```

**状态码**

| 场景 | 码 |
| --- | --- |
| 查到 / 改成功 | 200 |
| 创建成功 | 201 |
| 删除成功（无响应体） | 204 |
| 业务参数错 | 400 |
| 查不到 | 404 |
| 唯一键冲突 | 409 |
| 格式校验失败 | 422 |

**测试**

```python
with TestClient(app) as client:
    r = client.get("/users/1")
    assert r.status_code == 200
```

**三句话**

1. schema 管格式，service 管业务，router 只管 HTTP
2. 201 创建、204 删除、409 冲突、422 格式
3. 业务异常在 service 抛，在 main 统一映射

**下一步**：第七章把这些拼成完整项目——注册登录、密码哈希、角色权限、自动化测试。

---

<small>相关：[第五章 -- SQLAlchemy 进阶](../../ch05/notes/SQLAlchemy%20进阶.md) · [架构说明](../../../docs/ARCHITECTURE.md)</small>
