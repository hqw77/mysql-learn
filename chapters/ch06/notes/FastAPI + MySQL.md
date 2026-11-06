# 第六章 · FastAPI 接口开发

## 6.1 学习目标

本章把前几章的数据访问能力封装为 HTTP 接口,具体包括：

1. 理解接口开发中的三层结构及各自职责
2. 掌握用 Pydantic 定义请求模型与响应模型,并实现参数校验
3. 掌握用 APIRouter 定义接口并注册到应用
4. 理解常用 HTTP 状态码的语义,并能在接口中正确声明
5. 掌握业务异常到 HTTP 状态码的映射方式
6. 能够使用 TestClient 对接口进行自测

前置知识：第四章（service 层）、第五章（关系映射）。

> **本章的读法**：正文是教材写法。每个关键概念后面有一个「通俗理解」框。
> 本章三个案例都不需要启动服务器即可运行。

---

## 6.2 分层结构

### 6.2.1 三层职责

| 层 | 目录 | 职责 | 禁止事项 |
| --- | --- | --- | --- |
| 接口层 | `project/app/routers/` | 接收请求、返回响应、声明状态码 | 写 SQL、开事务 |
| 业务层 | `project/app/services/` | 业务规则、事务边界、抛业务异常 | 感知 HTTP |
| 模型层 | `project/app/models/` | 表结构映射 | 业务判断 |

此外还有两个辅助层：

| 目录 | 职责 |
| --- | --- |
| `project/app/schemas/` | 定义请求/响应的数据结构,并做格式校验 |
| `project/app/core/` | 配置、异常定义等公共设施 |

> **通俗理解**：一家餐厅分三块——前厅负责点单上菜,后厨负责做菜,仓库负责存食材。前厅不需要知道菜怎么做,后厨也不需要管客人坐哪。这样店大了才不乱。

### 6.2.2 请求处理流程

```plain
   客户端（浏览器 / curl / 前端）
        │  POST /users   {"username": "小明", "phone": "138..."}
        ▼
   ┌─────────────┐
   │  schemas/   │  ① 校验格式,不合格直接返回 422
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │  routers/   │  ② 接收请求,调用 service
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │  services/  │  ③ 执行业务,管理事务,抛业务异常
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │  models/    │  ④ 通过 ORM 访问数据库
   └──────┬──────┘
          ▼
        MySQL
```

异常沿相反方向回传,最终由应用入口的异常处理器翻译成 HTTP 响应。

---

## 6.3 请求与响应模型

### 6.3.1 作用

Pydantic 模型用于定义接口的输入输出结构,承担三项职责：

| 职责 | 说明 |
| --- | --- |
| 格式校验 | 类型、长度、格式、范围不合规时自动拒绝 |
| 响应裁剪 | 只返回模型声明的字段,避免泄露内部字段 |
| 生成文档 | `/docs` 中的参数说明由此自动生成 |

### 6.3.2 请求模型定义

```python
from decimal import Decimal
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50, description="用户名,2~50 字符")
    phone: str = Field(pattern=r"^1\d{10}$", description="手机号,11 位,1 开头")
    balance: Decimal = Field(default=Decimal("0.00"), ge=0, description="初始余额")
```

常用约束：

| 约束 | 含义 |
| --- | --- |
| `min_length` / `max_length` | 字符串长度范围 |
| `pattern` | 正则匹配 |
| `ge` / `le` | 数值大小范围（大于等于 / 小于等于） |
| `default` | 缺省值 |

### 6.3.3 响应模型定义

```python
from pydantic import ConfigDict

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)     # 允许直接接收 ORM 对象

    id: int
    username: str
    phone: str
    balance: Decimal
    is_deleted: bool
    created_at: datetime
```

配置 `from_attributes=True` 之后,路由函数可以直接 `return user`,FastAPI 会自动把 ORM 对象转换为 JSON。

> **通俗理解**：schema 是机场安检——先检查你带的东西合不合格,不合格当场拦下,后面的流程根本不会开始。响应模型则像一张"对外公开的信息表",只列该给客户看的字段。

### 6.3.4 校验失败的示例

示例文件：`chapters/ch06/code/01_schemas.py`

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

**注意**：schema 只能校验格式,无法校验业务规则。"用户名是否已存在"需要查询数据库,属于 service 层的职责。

---

## 6.4 路由

### 6.4.1 作用

路由负责把"请求路径 + HTTP 方法"映射到具体的处理函数。

### 6.4.2 定义方法

```python
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=UserPage)
def list_users(...): ...

@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, ...): ...

@router.post("", response_model=UserOut, status_code=201)
def create_user(...): ...
```

`prefix` 会加到所有路径前面,`tags` 用于在文档中分组。

### 6.4.3 注册路由

定义之后必须在应用入口注册,否则访问返回 404：

```python
from app.routers import health, users

app.include_router(health.router)
app.include_router(users.router)
```

### 6.4.4 本章的接口清单

| 方法 | 路径 | 说明 | 成功状态码 |
| --- | --- | --- | --- |
| GET | `/health` | 进程存活探测 | 200 |
| GET | `/health/db` | 数据库连通探测 | 200 |
| GET | `/users` | 用户列表（分页） | 200 |
| GET | `/users/{user_id}` | 用户详情 | 200 |
| POST | `/users` | 创建用户 | 201 |
| PUT | `/users/{user_id}/balance` | 调整余额 | 200 |
| DELETE | `/users/{user_id}` | 删除用户（软删） | 204 |

> **通俗理解**：路由像医院分诊台——你说"我头疼",它让你去内科；你说"我要退号",它指你去另一个窗口。分诊依据就是"路径 + 方法"。

---

## 6.5 状态码

### 6.5.1 常用状态码

| 状态码 | 含义 | 产生位置 |
| --- | --- | --- |
| 200 | 请求成功 | 默认 |
| 201 | 资源创建成功 | 路由中显式声明 |
| 204 | 成功但无响应体 | 路由中显式声明 |
| 400 | 业务参数不合法 | service 抛异常 |
| 404 | 资源不存在 | service 抛 `NotFoundError` |
| 409 | 资源冲突（如唯一键重复） | service 抛 `ConflictError` |
| 422 | 请求格式校验失败 | FastAPI 自动返回 |
| 500 | 未捕获的服务端异常 | 框架默认 |

### 6.5.2 声明方式

```python
@router.post("", status_code=201)          # 创建
def create_user(...): ...

@router.delete("/{user_id}", status_code=204)   # 删除
def delete_user(...): ...
```

不声明时默认为 200,因此 201 与 204 必须显式指定。

**注意**：状态码 204 表示"成功但没有响应体",处理函数不应返回任何内容。

> **通俗理解**：状态码像办完事递给你的回执单——200 是"办好了,结果在这",201 是"新办了一个,编号在这",204 是"办好了,没东西给你",422 是"你材料不合格,还没开始办"。

---

## 6.6 异常处理

### 6.6.1 业务异常定义

业务异常定义在 `project/app/core/exceptions.py`,自身携带状态码：

```python
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    def __init__(self, message="资源不存在"):
        super().__init__(message, status_code=404)

class ConflictError(AppError):
    def __init__(self, message="资源冲突"):
        super().__init__(message, status_code=409)
```

### 6.6.2 统一映射

在应用入口注册异常处理器,把业务异常翻译为 HTTP 响应：

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

于是 service 层只需 `raise NotFoundError("用户 1 不存在")`,客户端会收到：

```json
{"detail": "用户 1 不存在"}
```

**注意**：service 层应当抛业务异常,而不是 `HTTPException`。后者会让业务逻辑依赖 Web 框架,无法在命令行工具或定时任务中复用。

### 6.6.3 各状态码的产生位置

```plain
   客户端请求
      │
      ▼
   ① 422  ← schema 校验失败（尚未进入业务逻辑）
      │
      ▼
   ② 404  ← service 抛 NotFoundError
   ② 409  ← service 抛 ConflictError
      │
      ▼
   ③ 200 / 201 / 204  ← service 正常返回
```

### 6.6.4 示例与运行结果

示例文件：`chapters/ch06/code/03_api_write.py`

```plain
--- ① 创建用户 → 201 ---
    状态码: 201

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
```

> **通俗理解**：后厨做菜做砸了,不应该直接喊给客人听；服务员要翻译成客人能懂的话。`IntegrityError: Duplicate entry` 就是后厨的术语,"这个用户名已经有人用了"才是客人能听懂的。

---

## 6.7 分页接口

分页接口需要同时返回数据与分页信息：

```python
@router.get("", response_model=UserPage)
def list_users(
    page: int = Query(1, ge=1, description="页码,从 1 开始"),
    size: int = Query(10, ge=1, le=100, description="每页条数,最大 100"),
    db: Session = Depends(get_db),
) -> UserPage:
    items, total = user_service.list_users(db, page=page, size=size)
    return UserPage(total=total, page=page, size=size, items=items)
```

响应结构：

```json
{
  "total": 3,
  "page": 1,
  "size": 10,
  "items": [ ... ]
}
```

设计要点：

1. `size` 必须设置上限（如 `le=100`）,防止客户端请求过多数据；
2. `total` 来自 `COUNT(*)`,不是当前页的条数；
3. 分页信息与数据放在同一对象中,便于前端一次取全。

---

## 6.8 接口测试

### 6.8.1 TestClient

`TestClient` 可以直接向应用发送请求,无需启动 uvicorn 服务：

```python
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    r = client.get("/users/1")
    print(r.status_code, r.json())
```

使用 `with` 语句可以确保应用的生命周期事件（启动、关闭）被正确触发。

### 6.8.2 示例与运行结果

示例文件：`chapters/ch06/code/02_api_read.py`

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

--- ⑥ 打开文档看看 ---
    已注册的接口: ['/health', '/health/db', '/users', '/users/{user_id}', '/users/{user_id}/balance']
```

> **通俗理解**：不用等客人上门,厨师自己端一盘走一遍完整流程。接口测试就是这个意思——自己发请求、自己看响应,第七章的自动化测试也是用这套工具。

---

## 6.9 常见错误

| 错误信息 | 原因 | 解决方法 |
| --- | --- | --- |
| 接口返回 404 但路径无误 | 路由未注册 | 在 `main.py` 中 `include_router` |
| `ModuleNotFoundError: No module named 'app'` | 未在仓库根目录执行 | `cd` 到仓库根目录 |
| 返回 500 且无日志 | 异常未被捕获 | 业务异常应继承 `AppError` |
| `response_model` 报字段缺失 | ORM 对象缺字段或字段名不符 | 配置 `from_attributes=True` 并核对字段名 |
| 422 但请求体看起来正确 | 类型不匹配（如字符串传给了数字字段） | 检查 `detail` 中提示的字段 |
| `Decimal` 被序列化为字符串 | Pydantic 默认行为 | 前端按字符串处理,避免浮点精度问题 |

---

## 6.10 本章小结

1. 接口开发遵循三层结构：`routers` 只处理 HTTP,`services` 处理业务与事务,`models` 描述表结构。
2. Pydantic 模型负责格式校验与响应裁剪,`from_attributes=True` 使其可直接接收 ORM 对象。
3. 201、204 必须显式声明；422 由框架自动产生,404 与 409 由业务异常映射而来。
4. 业务异常应继承自定义基类,由应用入口统一映射为 HTTP 响应,service 层不应依赖 `HTTPException`。
5. 分页接口需返回 `total/page/size/items` 四部分,`size` 必须设上限。
6. `TestClient` 可在不启动服务器的情况下完成接口自测,也是后续编写自动化测试的基础。

---

## 6.11 练习

1. 新增一个 `GET /users/search?keyword=` 接口,支持按用户名模糊搜索,并支持分页。
2. 为 `DELETE /users/{id}` 增加"恢复"接口 `POST /users/{id}/restore`,把 `is_deleted` 改回 0。
3. 给创建用户接口增加一条业务规则：余额不能超过 100000,超出时返回 400,并写出对应的异常类。
4. 用 `TestClient` 写一段脚本,验证"创建 → 查询 → 删除 → 再查"的完整流程。

---

<small>相关：[第五章 -- SQLAlchemy 关系映射](../../ch05/notes/SQLAlchemy%20进阶.md) · [架构说明](../../../docs/ARCHITECTURE.md)</small>
