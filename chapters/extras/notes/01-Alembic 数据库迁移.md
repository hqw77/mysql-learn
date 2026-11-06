# 番外01 · Alembic 数据库迁移

> 这篇是 [第三章](../../ch03/notes/SQLAlchemy%20ORM%20基础.md) 的补充材料。
> 第三章只讲到"定义模型 + 查出一条数据",没讲怎么让数据库结构跟着模型一起变。本文补上这部分。

---

## 1. 什么时候需要 Alembic

| 场景 | 需要 Alembic 吗 |
| --- | --- |
| 本地练习,表随便建 | 不需要,`create_all` 够用 |
| 表里已经有数据,要加一列 | **需要** |
| 多人协作,别人也要同步表结构 | **需要** |
| 上线后要能回滚 | **需要** |
| 只想检查模型和库是否一致 | 不需要,`alembic check` 就够 |

> **通俗理解**:`create_all` 只会给"还没有的表"建表。表已经存在时,你加字段、改类型,它一概不管。而 Alembic 是"版本控制",每一版改动都有记录,可以前进也可以回退。

---

## 2. 为什么不用 create_all

```python
Base.metadata.create_all(engine)
```

这个方法只做一件事:创建缺失的表。

| 你想做的事 | `create_all` 的反应 |
| --- | --- |
| 新建一张表 | 会建 |
| 给已有表加一列 | 什么都不做 |
| 改字段类型 | 什么都不做 |
| 加索引 | 什么都不做 |

而本书的库里已经有真实数据:`students` 4 行、`orders` 3 行、`big_users` 99,822 行。表结构一旦要变,`create_all` 帮不上忙。

---

## 3. 三个基本概念

| 概念 | 含义 |
| --- | --- |
| `revision` | 一个迁移版本,对应 `migrations/versions/` 下的一个 Python 文件 |
| `upgrade()` / `downgrade()` | 该版本前进、回退时执行的具体 DDL |
| `alembic_version` 表 | 记录当前数据库处于哪个版本 |

> **通俗理解**:就像代码的 git 历史——每个 revision 是一次提交,`alembic_version` 表记录"我现在在哪个提交上"。`upgrade` 是往前翻,`downgrade` 是往回翻。

---

## 4. 初始化

在项目根目录执行:

```bash
alembic init migrations
```

生成的结构:

```plain
alembic.ini
migrations/
├── env.py              # 运行时环境,需要改这里
├── script.py.mako      # 新建迁移文件时的模板
└── versions/           # 每个迁移一个文件
```

`migrations/env.py` 中需要改动的三处:

```python
import app.models                              # ① 导入模型,否则发现不了表
from app.core.config import settings
from app.db.base import Base

config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))   # ②
target_metadata = Base.metadata                # ③ 告诉 Alembic 模型在哪
```

**说明**:

1. `import app.models` 不能省,模型不导入就不会注册到 `metadata`;
2. 连接串从配置读取,不写死在 `alembic.ini` 里,这样密码只维护一份;
3. 密码中的 `%` 会被 configparser 当成插值符号,必须转义为 `%%`。

> **通俗理解**:`env.py` 是 Alembic 的"启动脚本"。它得知道两件事——怎么连数据库(②)、模型定义在哪(①③)。这两样不知道,它就既连不上库,也看不出表结构差异。

---

## 5. 为已有数据的库建立基线

库里的表已经存在,直接执行 `alembic upgrade head` 会报 `Table already exists`。正确顺序是**先写迁移文件,再标记为已执行**:

```bash
# 1. 手写第一个 revision,内容等于现有表的 DDL
#    migrations/versions/0001_initial_schema.py

# 2. 标记为"已执行",但不真的执行 DDL
alembic stamp head

# 3. 确认
alembic current        # 输出 0001_initial (head)
alembic check          # 输出 No new upgrade operations detected.
```

`alembic_version` 表最终只有一行:

```plain
version_num
-----------
0001_initial
```

> **通俗理解**:这叫"先上车后补票"。表我早就建好了,现在只是告诉 Alembic——"这个版本对应的活我已经干完了,你记一笔就行,别再执行一遍"。

---

## 6. 给已有表新增字段

以给 `users` 加 `password_hash` 为例:

```bash
# 1. 先改模型
#    app/models/user.py 中增加:
#    password_hash: Mapped[str] = mapped_column(String(255))

# 2. 生成迁移文件
alembic revision --autogenerate -m "add password_hash to users"

# 3. 打开生成的文件,人工检查一遍
#    migrations/versions/xxxx_add_password_hash_to_users.py

# 4. 应用
alembic upgrade head
```

**注意**:必须人工检查 autogenerate 的结果。它不是万能的——字段重命名会被识别成"删一列 + 加一列",数据会丢。

> **通俗理解**:autogenerate 是"猜你要做什么",猜得不一定对。它像自动生成的 commit message,提交前你总得看一眼。

本书第五章就用了这套流程新增 `roles` 与 `user_roles` 两张表:

```bash
alembic upgrade head
alembic current        # 输出 0002_roles (head)
```

---

## 7. 常见坑:autogenerate 会删表

第一次执行 `alembic check` 时,输出如下:

```plain
Detected removed table 'orders'
Detected removed table 'authors'
Detected removed table 'big_users'
...
```

原因:第一章还留下 10 张练习表,它们没有对应的 ORM 模型。autogenerate 的判断逻辑是"库里有、模型里没有 → 判定为要删除"。

如果此时执行 `alembic revision --autogenerate`,生成的迁移文件里就是一串 `DROP TABLE`,`upgrade` 之后数据全部丢失。

解决办法是在 `migrations/env.py` 中加过滤:

```python
def include_object(object_, name, type_, reflected, compare_to):
    """数据库中存在但模型未定义的对象,一律忽略。"""
    if reflected and compare_to is None:
        return False
    return True
```

然后传给 `context.configure(..., include_object=include_object)`。

> **通俗理解**:这条规则的含义是——Alembic 只负责"模型里写过的表",练习表不归它管。否则它会把不认识的表当成"你不再需要了",顺手删掉。

---

## 8. 常用命令

| 命令 | 作用 |
| --- | --- |
| `alembic current` | 查看当前数据库处于哪个版本 |
| `alembic history` | 查看所有版本列表 |
| `alembic check` | 检查模型与数据库是否存在差异(不生成文件) |
| `alembic revision -m "说明"` | 创建空迁移文件,手写 DDL |
| `alembic revision --autogenerate -m "说明"` | 按模型差异自动生成迁移 |
| `alembic upgrade head` | 升级到最新版本 |
| `alembic upgrade +1` | 前进一个版本 |
| `alembic downgrade -1` | 回退一个版本 |
| `alembic downgrade base` | 全部回退 |
| `alembic stamp head` | 只记录版本号,不执行 DDL |
| `alembic upgrade head --sql` | 只输出 SQL,不连数据库(离线模式) |

---

## 9. 常见错误

| 错误信息 | 原因 | 解决方法 |
| --- | --- | --- |
| `UnicodeDecodeError: 'gbk' codec can't decode` | `alembic.ini` 中含中文,Alembic 用系统编码读取 | 该文件必须保持纯 ASCII,注释也用英文 |
| `Table 'xxx' already exists` | 表已存在,仍执行了初始迁移 | 用 `alembic stamp head` 代替 `upgrade` |
| autogenerate 生成大量 `DROP TABLE` | 库中存在未建模的表 | 在 `env.py` 中增加 `include_object` |
| `alembic check` 报告 comment 差异 | 模型中的 `comment` 与库中不一致 | 对齐注释,或删除模型中的 comment |
| `Can't locate revision identified by 'xxx'` | 本地版本文件被删除 | 检查 `versions/` 目录,必要时用 `stamp` 修正 |
| 多人协作出现两个 head | 两人从同一版本各自新增迁移 | `alembic merge -m "merge" <rev1> <rev2>` |

---

## 10. 小结

1. `create_all` 只创建缺失的表,不修改已有结构,也不记录版本,因此不适合有数据的项目。
2. Alembic 用 `revision` 记录每次结构变更,`alembic_version` 表记录当前版本。
3. `env.py` 需要配置三件事:导入模型、注入连接串、指定 `metadata`。
4. 已有数据的库应先手写基线迁移,再用 `alembic stamp head` 标记,而不是直接 `upgrade`。
5. autogenerate 必须人工检查;库中存在未建模的表时,需用 `include_object` 过滤,否则会生成 `DROP TABLE`。
6. `alembic.ini` 必须保持纯 ASCII,否则在 Windows 下会因编码问题读取失败。

---

## 11. 练习

1. 为 `users` 表增加 `email` 字段,走完整的"改模型 → 生成迁移 → 检查 → 升级"流程,然后用 `downgrade -1` 回退,确认字段被删除。
2. 执行 `alembic history`,观察 `0001` 与 `0002` 的父子关系(`down_revision`)。
3. 临时删除 `env.py` 中的 `include_object`,执行 `alembic check`,观察输出差异,然后恢复。
4. 思考:如果两个人同时基于 `0002` 各自新增一个迁移,`alembic upgrade head` 会发生什么?

---

<small>相关:[第三章 -- SQLAlchemy ORM 基础](../../ch03/notes/SQLAlchemy%20ORM%20基础.md) · [第五章 -- SQLAlchemy 关系映射](../../ch05/notes/SQLAlchemy%20进阶.md)</small>
