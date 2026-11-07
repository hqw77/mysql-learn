# 项目代码导读

> 适用对象:已经跑通 `project/`、想读懂这 893 行代码的人。
> 阅读方式:**跟着一个请求走完整链路**,不要按目录顺序从 `__init__.py` 读起。
> 每一站都附有答案,先想再看。

## 0. 怎么用这份文档

| 项 | 建议 |
| --- | --- |
| 总时长 | 约 2 小时,分三次 |
| 前置 | 服务能启动,`/docs` 能打开 |
| 配套动作 | 打开 `DB_ECHO=true` 观察 SQL；读完一站实际调一次接口 |
| 判断标准 | 能不看代码画出调用链、答出自检 5 问 |

代码规模:

| 目录 | 行数 | 说明 |
| --- | --- | --- |
| `project/app` | 893 | 应用代码,26 个文件 |
| `project/tests` | 159 | 8 个用例 |
| `project/migrations` | 223 | 3 个版本 |

---

## 1. 入口:`main.py`(37 行)

```python
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(wallet.router)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

这 6 行说明:每个 `router` 对应一个文件,`main.py` 只负责挂载与统一异常。

**答案:为什么一个处理器能管 404、409、401、403?**

因为四个异常都继承自 `AppError`:

```python
class AppError(Exception):          # 基类,状态码 400
class NotFoundError(AppError):      # 404
class ConflictError(AppError):      # 409
class UnauthorizedError(AppError):  # 401
class ForbiddenError(AppError):     # 403
```

`@app.exception_handler(AppError)` 会拦截这个类**及其所有子类**,读取 `exc.status_code` 决定响应码。所以 service 层可以直接 `raise NotFoundError(...)`,完全不感知 HTTP。

---

## 2. 一条读请求:`GET /users/{id}`

调用链:

```plain
GET /users/1
  ├─→ routers/users.py:27        get_user(user_id: int, db)
  ├─→ services/user_service.py:38  db.get(User, 1)
  ├─→ models/user.py:22          User 类(表结构)
  └─→ schemas/user.py:29         UserOut(只暴露 6 个字段)
```

### 2.1 路由层

```python
# routers/users.py:27
@router.get("/{user_id}", response_model=UserOut, summary="用户详情")
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    return user_service.get_user(db, user_id)
```

整个函数体只有一行。

**答案 ①:`user_id` 从哪来?**

从 URL 路径 `/{user_id}` 来。FastAPI 依据参数注解 `int` 把字符串 `"1"` 自动转成整数。传 `abc` 会直接返回 422,进不到函数体。

**答案 ②:`db` 从哪来?**

`Depends(get_db)`。FastAPI 在调用函数前先执行 `get_db()`,把 Session 注入进来。

### 2.2 业务层

```python
# services/user_service.py:38
def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"用户 {user_id} 不存在")
    return user
```

**答案 ③:404 是谁抛的?**

是 `get_user` 主动抛的 `NotFoundError`。抛出后经 `main.py` 的处理器转成 `404 {"detail": "用户 1 不存在"}`。

注意 `db.get()` 本身不抛异常——查不到只是返回 `None`,是 service 把它翻译成业务异常。

### 2.3 响应层

```python
# schemas/user.py:29
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    phone: str
    balance: Decimal
    is_deleted: bool
    created_at: datetime
    # 没有 password_hash
```

**答案 ④:为什么响应里没有 `password_hash`?**

两个原因叠加:

1. `UserOut` 没声明这个字段；
2. 路由写了 `response_model=UserOut`,FastAPI 按模型裁剪输出。

`from_attributes=True` 是关键——它让 Pydantic 读对象的属性(`user.username`),而不是只读字典的键,因此 `return user`(ORM 对象)也能被正确序列化。

---

## 3. 一条写请求:`POST /users`

调用链:

```plain
请求体 {"username":"ab","phone":"123",...}
  ├─→ schemas/user.py:15    UserCreate 校验:长度、正则、非负
  ├─→ routers/users.py:38   create_user(payload, db)
  ├─→ services/user_service.py:20
  │       add → commit → 撞唯一键则 rollback + 抛 ConflictError
  └─→ db.refresh(user)      读回 id 与 created_at
```

```python
# schemas/user.py:15
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r"^1\d{10}$")
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)
```

```python
# services/user_service.py:20
def create_user(db, username, phone, balance=Decimal("0.00")) -> User:
    user = User(username=username, phone=phone, balance=balance)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:          # 唯一键冲突在这里才会暴露
        db.rollback()
        raise ConflictError(f"用户名或手机号已存在：{username}") from exc
    db.refresh(user)
    return user
```

**答案 ⑤:用户名校验在哪一层?**

分两处,职责不同:

| 校验 | 位置 | 结果 |
| --- | --- | --- |
| 长度、格式 | `UserCreate`(schema) | 不合格 → 422,未进入业务逻辑 |
| 是否重名 | `create_user`(service) | 重复 → 409 |

分工原则:**格式错误归 schema,业务冲突归 service。**

**答案 ⑥:那个 `try/except` 为什么不能省?**

并发场景:

```plain
请求 A:INSERT username='abc' → commit ✓
请求 B:INSERT username='abc' → 唯一索引挡住 → IntegrityError
```

只有数据库的唯一索引能最终兜底。捕获后**必须 `rollback()`**,否则 Session 卡在坏事务里,后续操作全部报 `PendingRollbackError`。

**答案 ⑦:`db.refresh(user)` 干什么?**

`commit()` 之后,主键由数据库生成,`created_at` 这类 `server_default` 字段在对象里仍可能是空值。`refresh` 会再 SELECT 一次,把真实值同步回对象。

补充:`session.py` 里设了 `expire_on_commit=False`,所以 commit 后属性不会自动过期,`return user` 时不会触发额外查询。

**答案 ⑧:201 与 204 在哪声明?**

```python
@router.post("", status_code=status.HTTP_201_CREATED)                    # 创建
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)     # 删除
```

默认是 200,这两个必须显式声明；204 还要求函数返回 `None`。

---

## 4. 认证主线

### 4.1 加密工具:`core/security.py`(47 行)

```python
_hasher = PasswordHasher()

def hash_password(raw: str) -> str:
    return _hasher.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
```

**答案 ⑨:为什么不能 `hash_password(raw) == hashed`?**

argon2 **每次生成新的随机盐**,同一密码两次哈希结果完全不同:

```plain
$argon2id$v=19$m=65536,t=3,p=4$MfkBzFo...$5fyU7Meh...
$argon2id$v=19$m=65536,t=3,p=4$QpwLCTs...$T+KZJwYP...
```

只能把「盐 + 参数 + 哈希」整套交给 `verify()`,由它重算后比对。

```python
def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
```

**答案 ⑩:payload 里为什么只放 user_id?**

因为 **JWT 的 payload 是 Base64 编码,不是加密**。任何人拿到令牌都能解开看到内容。

因此只放不敏感的标识:用户 id、签发时间、过期时间。密码、手机号、身份证一律不放。

### 4.2 注册与登录:`services/auth_service.py`(44 行)

```python
def register(db, username, phone, password) -> User:
    exists = db.scalar(
        select(User).where(or_(User.username == username, User.phone == phone))
    )
    if exists is not None:
        raise ConflictError("用户名或手机号已被注册")

    user = User(username=username, phone=phone, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("用户名或手机号已被注册") from exc
    db.refresh(user)
    return user
```

```python
def authenticate(db, username, password) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or user.is_deleted:
        raise UnauthorizedError("用户名或密码错误")
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误")
    return user
```

**答案 ⑪:密码从明文到入库,经过哪几步?**

```plain
① 请求体 {"password": "secret123"}      明文,靠 HTTPS 保护传输
② UserCreate 校验 min_length=6           仍在内存
③ hash_password()                        $argon2id$...（约 32ms）
④ User(password_hash=...)                对象里只有哈希
⑤ db.commit()                           INSERT 进库
```

明文只在前两步存在,之后不再出现。

**答案 ⑫:为什么两种情况都返回"用户名或密码错误"?**

分开提示会泄露信息:

```plain
"用户不存在" → 攻击者知道该用户名未注册
"密码错误"   → 攻击者知道该用户名已注册
```

这叫**账号枚举**。攻击者可先扫出全部已注册用户,再针对性撞库。所以两种情况必须返回同一句话。

### 4.3 鉴权依赖:`deps.py`(59 行)

```python
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("缺少访问令牌")
    try:
        user_id = decode_access_token(credentials.credentials)
    except PyJWTError:
        raise UnauthorizedError("令牌无效或已过期")
    user = db.get(User, user_id)
    if user is None or user.is_deleted:
        raise UnauthorizedError("用户不存在或已注销")
    return user
```

**答案 ⑬:这里有几个 401?分别什么情况?**

三个,对应三行 `raise`:

| 情况 | 触发条件 | 提示 |
| --- | --- | --- |
| ① | 请求头没有 `Authorization: Bearer xxx` | 缺少访问令牌 |
| ② | 令牌被篡改、签名不符、或已过期 | 令牌无效或已过期 |
| ③ | 令牌有效但用户已软删 | 用户不存在或已注销 |

`auto_error=False` 的作用:若用默认 `True`,没带令牌时 FastAPI 会抛框架固定的 403,就无法统一成自己的 401 与中文提示。

```python
def require_role(*role_names: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        owned = {role.name for role in current_user.roles}
        if not owned & set(role_names):
            raise ForbiddenError(f"需要角色之一：{', '.join(role_names)}")
        return current_user
    return checker
```

**答案 ⑭:`require_role("admin")` 为什么返回一个函数?**

`Depends(...)` 需要一个可调用对象,而我们又想传入「需要哪个角色」。

外层 `require_role` 是**工厂**:调用它、传入角色名,它产出一个绑定好角色的 `checker`。这样同一个函数能生成任意角色的校验器,不必为 admin、editor 各写一份。

**答案 ⑮:401 与 403 差在哪?**

```plain
401 = 我不知道你是谁          → 没带令牌 / 令牌无效
403 = 我知道你是谁,但权限不够 → 已登录,角色不匹配
```

代码上:401 全部出现在 `get_current_user`,403 全部出现在 `checker`。

---

## 5. 事务:`transfer`

```python
# services/user_service.py:111
def transfer(db, from_id, to_id, amount) -> tuple[User, User]:
    if amount <= 0:
        raise AppError("转账金额必须大于 0")
    if from_id == to_id:
        raise AppError("不能给自己转账")

    src = get_user(db, from_id)
    dst = get_user(db, to_id)
    if src.balance < amount:
        raise AppError(f"余额不足,当前余额 {src.balance}")

    try:
        src.balance = src.balance - amount
        dst.balance = dst.balance + amount
        db.commit()                  # 两条 UPDATE 在同一事务
    except Exception:
        db.rollback()
        raise

    db.refresh(src)
    db.refresh(dst)
    return src, dst
```

**答案 ⑯:如果写两次 `db.commit()` 会怎样?**

```python
src.balance -= amount
db.commit()          # ① 甲的改动已落库
dst.balance += amount
db.commit()          # ② 若此处报错
```

②失败时①已经提交,回不去了。结果是甲扣了钱、乙没收到,钱凭空消失。

结论:**一个业务操作 = 一个事务 = 只 commit 一次。**

**答案 ⑰:那些 `if` 校验为什么不放进 `try`?**

它们抛的是业务异常(400),此时还没有任何写操作,Session 是干净的,不需要回滚。只有真正改过数据之后才需要 `try/rollback`。

另外注意最后的 `raise` 是裸的——保留原始堆栈继续向上抛,不会被吞掉。

---

## 6. 地基

### 6.1 `db/engine.py`(15 行)

```python
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,                     # 取连接前先探活
    pool_size=settings.db_pool_size,        # 常驻 5 条
    max_overflow=settings.db_max_overflow,  # 高峰最多再借 10 条
    pool_recycle=settings.db_pool_recycle,  # 1 小时后强制重建
    pool_timeout=settings.db_pool_timeout,  # 借不到最多等 30 秒
    echo=settings.db_echo,
)
```

**答案 ⑱:`pool_pre_ping` 和 `pool_recycle` 为什么都要?**

- MySQL 默认 8 小时无活动即断开；
- 池中连接被服务端断开后,客户端并不知情；
- `pre_ping`:每次借出前先探活,发现断开就换一条(治标)；
- `recycle`:存活超过 3600 秒主动换新(治本)。

两者互补,缺一个都会在特定时间点遇到 `Lost connection to MySQL server`。

### 6.2 `db/session.py`(28 行)

```python
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**答案 ⑲:`yield` 的 `finally` 为什么一定执行?**

FastAPI 在请求结束(正常返回或抛异常)时会回到生成器,触发 `finally`,因此连接必然归还。

若写成 `return db` 就没有这个保证——普通函数拿不到"请求结束"这个时机。

**答案 ⑳:`expire_on_commit=False` 有什么用?**

默认 `True` 时,commit 后所有属性被标记过期,下次访问 `user.id` 会**再查一次库**。

关掉后对象在 commit 后依然可用,直接 `return user` 不再发 SQL。这正是 `create_user` 里 `refresh` 之后能直接返回的原因。

### 6.3 `core/exceptions.py`(32 行)

```python
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)
```

四个子类只是把 `status_code` 固定住:404 / 409 / 401 / 403。

---

## 7. 横向检查:验证约定

按层再扫一遍,只看"有没有破坏规矩":

| 层 | 该有的特征 | 结果 |
| --- | --- | --- |
| `routers/` | 不出现 `select(`、不出现 `commit()` | 全部委托给 service |
| `services/` | 每个函数自己 commit,抛业务异常 | 一致 |
| `schemas/` | 只用 `BaseModel`,不碰数据库 | 一致 |
| `models/` | 只有字段与关系,无业务判断 | 一致 |
| `core/` | 不 import 上层模块 | 一致 |

验证方法:在 `routers/` 目录下搜 `select(` 与 `commit`,应为 0 处。这就是分层成功的样子。

---

## 8. 自检 5 问

能不看代码答出这 5 句,说明已经读透:

| # | 问题 | 答案 |
| --- | --- | --- |
| 1 | 一个请求经过哪几层,各干什么 | `routers`(HTTP) → `services`(业务+事务) → `models`(表结构)；异常反向回到 `main.py` 统一映射 |
| 2 | 404/409/401/403 谁抛的 | 都是 service 或 deps 抛的业务异常,由 `main.py` 转成 HTTP |
| 3 | 密码为什么不能比字符串 | argon2 每次随机盐,同一密码哈希结果不同,必须用 `verify()` |
| 4 | 转账为什么必须一个事务 | 两条 UPDATE 只 commit 一次,否则第二条失败时第一条已生效 |
| 5 | 表结构改了怎么同步 | `alembic revision --autogenerate` → 人工检查 → `alembic upgrade head` |

---

## 9. 常见误区

| 误区 | 正解 |
| --- | --- |
| 从 `__init__.py` 顺序读到尾 | 按请求链路读,先看一条最简的读请求 |
| 只看不跑 | 开 `DB_ECHO=true` 调接口,看 SQL 何时发出 |
| 以为 `db.get()` 查不到会报错 | 它返回 `None`,是 service 主动抛 404 |
| 以为 `close()` 是断开连接 | 是归还连接池 |
| 以为 JWT 内容是加密的 | 只是 Base64,任何人都能解 |
| 以为 `commit()` 会更新所有字段 | 脏检查只生成变化的列 |

---

## 10. 建议节奏

| 时间 | 读哪几站 | 约需 |
| --- | --- | --- |
| 第一次 | 第 1、2、3 站 | 45 分钟 |
| 第二次 | 第 4 站(最长,面试最常问) | 40 分钟 |
| 第三次 | 第 5、6、7 站 | 40 分钟 |

读完回看 `project/README.md` 的「设计说明」一节,每句话都能对应到具体代码。
