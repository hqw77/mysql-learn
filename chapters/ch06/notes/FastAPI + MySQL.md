# 第六章 · 把数据库变成接口（大白话版）

> 这一章讲的是：**别人怎么通过网络用上你写的数据库操作。**

---

## 这一章涉及哪些知识点

1. **三层分工**：前厅、后厨、仓库各管什么
2. **schema**：机场安检，先检查再放行
3. **路由**：分诊台，哪个窗口办哪件事
4. **状态码**：办事回执，201 / 404 / 409 / 422 各是什么意思
5. **异常变状态码**：后厨出问题，前台怎么跟客人说
6. **自己试菜**：不起服务器也能测接口

每个知识点都是：**一句话结论 → 打个比方 → 看代码 → 记住一个坑**。

---

## 先看一张「比喻地图」

| 你要干的事 | 生活里的比方 | 对应文件 |
| --- | --- | --- |
| 收请求、返响应 | 前厅服务员接单上菜 | `routers/` |
| 检查请求格式 | 机场安检 | `schemas/` |
| 真正干活 | 后厨做菜 | `services/` |
| 数据本身 | 仓库存食材 | `models/` |
| 告诉客人成功还是失败 | 递一张回执单 | 状态码 |
| 后厨搞砸了怎么解释 | 服务员话术 | 异常处理器 |
| 自己当客人试菜 | 内部试吃 | `TestClient` |

## 英文词小抄

| 英文 | 中文 | 一句人话 |
| --- | --- | --- |
| `schema` | 数据模型 | 定义接口收什么、返什么，也负责检查格式 |
| `router` | 路由 | 一组接口的集合，比如所有 `/users` 开头的 |
| `response_model` | 响应模型 | 声明返回的数据长什么样，多余的字段会被丢掉 |
| `Depends` | 依赖注入 | 让 FastAPI 自动把数据库会话递给你 |
| `Query` | 查询参数 | URL 里 `?page=1&size=10` 这些 |
| `status_code` | 状态码 | 200 成功、201 创建、404 找不到…… |
| `HTTPException` | HTTP 异常 | FastAPI 自带的错误，返回状态码 + 说明 |
| `TestClient` | 测试客户端 | 不用起服务器，直接把请求打进应用 |
| `422` | 校验失败 | 你传的数据格式不对，还没进业务逻辑就被挡了 |
| `409` | 冲突 | 数据撞车了，最常见是用户名重复 |

---

## 知识点 1：三层分工 —— 前厅、后厨、仓库

**一句话**：接口层只管收单返单，业务逻辑放 service，数据定义放 model。

**打个比方**

一家餐厅：

| 角色 | 对应文件 | 干什么 | 不该干什么 |
| --- | --- | --- | --- |
| 前厅服务员 | `routers/` | 迎客、点单、上菜 | 不该进厨房炒菜 |
| 后厨 | `services/` | 做菜，管火候和食材 | 不该管客人坐哪 |
| 仓库 | `models/` | 存食材（数据和结构） | 不该决定怎么做菜 |

如果让服务员自己炒菜，两三个客人还行，店一大就乱。

**看请求怎么走**

```plain
   客户端（浏览器 / curl / 前端）
        │  POST /users  {"username": "小明", ...}
        ▼
   ┌─────────────┐
   │  routers/   │ 前厅：收单，检查有没有这个人该办的窗口
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │  services/  │ 后厨：真正干活，管事务、管报错
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │  models/    │ 仓库：数据长什么样
   └──────┬──────┘
          ▼
        MySQL
```

**看代码**

```python
# routers/users.py —— 前厅，只有三行
@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, payload.username, payload.phone, payload.balance)

# services/user_service.py —— 后厨，所有业务逻辑在这
def create_user(db, username, phone, balance=Decimal("0.00")):
    ...
```

前厅里**一行 SQL 都没有**。这就是分层的意义。

**记住一个坑**

**别在路由里写业务逻辑。** 一旦写了，第二个接口要复用这段逻辑时，你就只能复制粘贴。第四章之所以要 service 层，就是为了这一刻。

---

## 知识点 2：schema —— 机场安检

**一句话**：请求先进 schema 检查格式，不合格当场拦下，根本到不了你的业务代码。

**打个比方**

坐飞机：

1. 你先过安检（schema 校验）——行李里有违禁品，当场拦下；
2. 过了安检才登机（进业务逻辑）；
3. 安检不会管你"是不是本航班的乘客"（那是业务规则）。

**看代码**

```python
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r"^1\d{10}$")
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)
```

这三行就定义了四条规则：用户名 2~50 字、手机号 11 位以 1 开头、余额不能是负数、不传余额默认 0。

**不合规会怎样**

真实运行结果：

```plain
--- ② 用户名太短（min_length=2） ---
    字段 username: String should have at least 2 characters

--- ③ 手机号格式不对 ---
    字段 phone: String should match pattern '^1\d{10}$'

--- ④ 余额为负 ---
    字段 balance: Input should be greater than or equal to 0

--- ⑤ 不传 balance 会怎样 ---
    balance 默认值: 0.00   ← 默认值生效
```

走接口时，这些错误会变成 **422**，而且你一行 `if` 都没写。

**记住一个坑**

**schema 挡不住业务规则。** 它能挡"格式错"，挡不住"用户名已存在"——后者要查数据库，是 service 的事。

跑一遍：`python chapters/ch06/code/01_schemas.py`

---

## 知识点 3：路由 —— 分诊台

**一句话**：路由就是"哪个 URL 配哪个函数"，一个文件管一组相关接口。

**打个比方**

医院分诊台：

- 你说"我头疼" → 分诊台让你去内科（`GET /users`）
- 你说"我要挂号" → 分诊台给你一张表去填（`POST /users`）
- 你说"我要退号" → 分诊台告诉你走哪个窗口（`DELETE /users/1`）

"路径 + 方法" 就是分诊台判断的依据。

**看代码**

```python
router = APIRouter(prefix="/users", tags=["users"])

@router.get("")                       # GET  /users
@router.get("/{user_id}")             # GET  /users/1
@router.post("")                      # POST /users
@router.put("/{user_id}/balance")     # PUT  /users/1/balance
@router.delete("/{user_id}")          # DELETE /users/1
```

**五个接口对应的真实路径**

```plain
/health                       探针
/health/db                    探针（查库）
/users                        列表（分页）
/users/{user_id}              详情 / 删除
/users/{user_id}/balance      改余额
```

**记住一个坑**

**路由注册了才有用。** 写完 `routers/users.py`，一定要在 `app/main.py` 里 `app.include_router(users.router)`，否则访问还是 404，而且报错很难懂。

---

## 知识点 4：状态码 —— 办事回执

**一句话**：状态码是告诉调用方"这件事办成了没有、为什么没成"。

**打个比方**

办完事，工作人员递给你一张回执：

| 回执 | 意思 |
| --- | --- |
| 200 | 办好了，结果在这 |
| 201 | 新办了一个，编号在这 |
| 204 | 办好了，没有东西给你（删除了） |
| 400 | 你带的东西不对（业务层面） |
| 404 | 没这个东西 |
| 409 | 撞车了（比如重名） |
| 422 | 你的材料格式不对（安检没过） |

**看代码**

```python
@router.post("", response_model=UserOut, status_code=201)     # 创建 → 201
def create_user(...): ...

@router.delete("/{user_id}", status_code=204)                 # 删除 → 204
def delete_user(...): ...
```

不写 `status_code` 就是默认 200。所以 201 和 204 要**显式声明**。

**记住一个坑**

**204 不能有响应体。** 你如果既声明 204 又 `return user`，FastAPI 会报错或者把响应搞乱。204 就是"办好了，没东西给你"。

---

## 知识点 5：异常变状态码 —— 服务员话术

**一句话**：后厨出问题，不该直接喊给客人听；前台要翻译成客人能懂的"话术"。

**打个比方**

- 后厨：`IntegrityError: Duplicate entry 'u123' for key 'users.username'`（客人听不懂）
- 服务员说：**"抱歉，这个用户名已经有人用了"**（客人听得懂，还知道该怎么办）

这就是"业务异常"的作用：把数据库报错翻译成人话。

**看代码**

```python
# services/user_service.py —— 后厨把技术错误翻译成业务异常
try:
    db.commit()
except IntegrityError:
    db.rollback()
    raise ConflictError(f"用户名或手机号已存在：{username}")

# app/core/exceptions.py —— 业务异常自带状态码
class ConflictError(AppError):
    def __init__(self, message): super().__init__(message, status_code=409)

# app/main.py —— 统一翻译成 HTTP 响应
@app.exception_handler(AppError)
async def handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

**状态码是谁产生的**

```plain
   客户端请求
      │
      ▼
   ① 422  ← schema 校验失败（还没进业务）
      │
      ▼
   ② 404  ← service 抛 NotFoundError
   ② 409  ← service 抛 ConflictError
      │
      ▼
   ③ 200 / 201 / 204  ← service 正常返回
```

**记住一个坑**

**service 里抛的应该是业务异常，不是 `HTTPException`。** 抛 HTTP 异常，这段逻辑就离不开 Web 框架了——写命令行工具、定时任务时没法复用。

跑一遍：`python chapters/ch06/code/03_api_write.py`

---

## 知识点 6：自己试菜 —— 不起服务器也能测

**一句话**：`TestClient` 把请求直接打进应用，不用启动 uvicorn。

**打个比方**

餐厅试菜：不用等客人来，厨师自己端一盘，走一遍完整流程。

**看代码**

```python
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    r = client.get("/users/1")
    print(r.status_code, r.json())
```

**真实结果**

```plain
--- ① 健康检查 ---
    状态码: 200  响应: {'status': 'ok'}

--- ② 用户列表（分页） ---
    状态码: 200
    total = 3  page = 1  size = 2

--- ④ 查不存在的用户 → 404 ---
    状态码: 404
    响应: {'detail': '用户 99999 不存在'}

--- ⑤ 参数不合法 → 422（FastAPI 自动挡） ---
    状态码: 422
    第一条错误: Input should be less than or equal to 100
```

**记住一个坑**

**别用 `client = TestClient(app)` 然后忘了关。** 用 `with TestClient(app) as client:`，退出时会正确触发应用的启动/关闭流程（包括关闭数据库连接池）。

跑一遍：`python chapters/ch06/code/02_api_read.py`

---

## 面试常问的 3 个问题

### 1. FastAPI 里怎么管理数据库连接？

> **一句话**：用依赖注入加 `yield`，每个请求一个 Session，请求结束自动归还。
>
> **展开**：
> 1. `get_db()` 是个生成器依赖：创建 Session → `yield db` → `finally: db.close()`；
> 2. 路由参数写 `db: Session = Depends(get_db)`，FastAPI 自动注入并在响应后执行 `finally`；
> 3. Session 只在执行 SQL 时才向 Engine 借连接，用完立刻还。
>
> **加分项**：`yield` 保证请求抛异常时也会关闭，避免连接泄漏——和第二章"忘记 close 会卡死池子"是同一个问题。

### 2. 400、422、409、500 分别代表什么？

> **一句话**：422 是格式错，400 是业务参数错，409 是冲突，500 是没兜住的异常。
>
> **展开**：
> - 422：Pydantic 校验失败（类型、长度、格式、范围），FastAPI 自动返回；
> - 400：格式对但业务不允许，比如"余额不足"；
> - 409：资源冲突，典型是唯一键重复；
> - 500：代码抛了没捕获的异常，属于 bug，不该出现在正常流程里。
>
> **加分项**：我们的做法是 service 抛 `AppError` 子类（404 / 409），`main.py` 统一映射，路由里一个 try 都不写。

### 3. 为什么要有 schema 层，直接用 ORM 模型不行吗？

> **一句话**：ORM 描述数据库，schema 描述接口，两者变更节奏不同。
>
> **展开**：
> 1. 安全：schema 是白名单，能挡住不该暴露的字段；
> 2. 稳定：数据库加一列，不会让接口响应突然多一个字段；
> 3. 校验：`min_length`、`pattern` 这类规则属于接口契约，不该写进表结构。
>
> **加分项**：`UserOut` 同时是响应模型和文档来源，`/docs` 里的字段说明就是从 `Field(description=...)` 自动生成的。

---

## 这一章只要记住三句话

1. **schema 管格式，service 管业务，router 只管 HTTP**
2. **201 创建、204 删除、409 冲突、422 格式**
3. **业务异常在 service 抛，在 main 统一映射**

---

## 练习顺序

```bash
cd D:/github_repository/mysql-learning
export MYSQL_PASSWORD=你的密码

python chapters/ch06/code/01_schemas.py      # 安检规则
python chapters/ch06/code/02_api_read.py     # 读接口 200/404/422
python chapters/ch06/code/03_api_write.py    # 写接口 201/409/204
```

也可以直接起服务看文档：

```bash
uvicorn app.main:app --reload
# 打开 http://127.0.0.1:8000/docs
```

---

## 学完可以自问三句

- 422 和 409 分别是谁产生的？
- 为什么 service 里不该抛 `HTTPException`？
- `get_db` 里的 `yield` 有什么用？

---

## 速查卡（忘了就翻这一页）

**三层骨架**

```python
# schemas/user.py —— 安检
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r"^1\d{10}$")

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # 能直接吃 ORM 对象
    id: int; username: str; balance: Decimal

# routers/users.py —— 前厅
@router.get("", response_model=UserPage)
def list_users(page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    items, total = user_service.list_users(db, page=page, size=10)
    return UserPage(total=total, page=page, size=10, items=items)

# main.py —— 挂上去
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

---

<small>相关：[第五章 -- 让表之间连起来](../../ch05/notes/SQLAlchemy%20进阶.md) · [架构说明](../../../docs/ARCHITECTURE.md)</small>
