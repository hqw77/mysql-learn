# 番外01 · Alembic 数据库迁移

> 这篇是 [第三章](../../ch03/notes/SQLAlchemy%20ORM%20基础.md) 的补充材料。
> 第三章只教到「定义模型 + 查出一条数据」，没讲怎么让数据库结构跟着模型变。本文补上。

## 0. 什么时候需要它

| 场景 | 需要 Alembic 吗 |
| --- | --- |
| 本地学习，表随便建 | 不需要，`create_all` 够用 |
| 表里有数据，要加一列 | **需要** |
| 多人协作，别人也要同步结构 | **需要** |
| 上线要能回滚 | **需要** |
| 只是想验证模型写得对不对 | 不需要，`alembic check` 就够 |

## 1. 为什么不用 `create_all`

```python
Base.metadata.create_all(engine)
```

它能用，但只做一件事：**创建缺失的表**。

- 表已存在？跳过，不检查、不修改
- 想加一列？什么都不做
- 想改类型、加索引？也什么都不做

你的库里已经有真实数据（`students` 4 行、`orders` 3 行、`big_users` 99,822 行），结构一旦要变，`create_all` 帮不上忙。

## 2. 三个概念

| 概念 | 含义 |
| --- | --- |
| `revision` | 一个迁移版本 = 一个 Python 文件 |
| `upgrade()` / `downgrade()` | 前进 / 回退的 DDL |
| `alembic_version` 表 | 记录当前库处在哪个 revision |

## 3. 初始化（本项目已完成）

```bash
alembic init migrations
```

生成了：

```plain
alembic.ini
migrations/
├── env.py              # 运行时环境，改这里
├── script.py.mako      # 新迁移文件的模板
└── versions/           # 每个迁移一个文件
```

`env.py` 里最关键的三行：

```python
import app.models                                    # ⚠️ 必须 import，模型才会注册
from app.core.config import settings
from app.db.base import Base

config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata
```

> 💡 连接串不写进 `alembic.ini`，而是从 `.env` 读。这样密码只维护一份，也不会进 git。
>
> ⚠️ 密码里的 `%` 会被 configparser 当成插值符号，必须 `.replace("%", "%%")`。

## 4. 给「已有数据的库」建基线

表已经在库里，直接 `alembic upgrade head` 会撞 `Table already exists`。正确顺序是**先写迁移，再 stamp**：

```bash
# 1. 手写第一个 revision，内容 = 现有表的 DDL
#    migrations/versions/0001_initial_schema.py

# 2. 标记为"已执行"，但不真的执行
alembic stamp head

# 3. 确认
alembic current     # 0001_initial (head)
alembic check       # No new upgrade operations detected.
```

本质上就是告诉 Alembic：「这个版本对应的表我已经建好了，你记一笔就行」。

## 5. 之后加一列怎么操作

以 `users` 表加 `password_hash` 为例：

```bash
# 1. 先改模型
#    app/models/user.py 里加一行
#    password_hash: Mapped[str] = mapped_column(String(255))

# 2. 自动生成迁移
alembic revision --autogenerate -m "add password_hash to users"

# 3. 打开生成的文件检查一遍！（重要）
#    migrations/versions/xxxx_add_password_hash_to_users.py

# 4. 应用
alembic upgrade head
```

> ⚠️ **永远要人工检查 autogenerate 的结果**。它不是万能的，列重命名会被识别成「删一列 + 加一列」，数据就没了。

## 6. 最大的坑：autogenerate 会删表

第一次跑 `alembic check`，输出是这样的：

```plain
Detected removed table 'orders'
Detected removed table 'authors'
Detected removed table 'big_users'
...
```

原因：库里还有第一章留下的 10 张练习表，它们**没有对应的 ORM 模型**。autogenerate 的判断逻辑是「库里有、模型没有 → 该删」。

这时候如果直接 `alembic revision --autogenerate`，生成的迁移里就是一串 `DROP TABLE`，`upgrade` 一下数据全没。

解决：在 `migrations/env.py` 加过滤。

```python
def include_object(object_, name, type_, reflected, compare_to):
    """库里存在但模型没定义的对象，一律不管。"""
    if reflected and compare_to is None:
        return False
    return True
```

然后传给 `context.configure(..., include_object=include_object)`。

> 💡 这条规则的含义要记牢：**Alembic 只负责"模型里写过的表"，练习表不归它管**。

## 7. 命令速查

| 命令 | 作用 |
| --- | --- |
| `alembic current` | 当前库在哪个版本 |
| `alembic history` | 所有版本列表 |
| `alembic check` | 模型与库是否有差异（不生成文件） |
| `alembic revision -m "说明"` | 建空迁移，手写 DDL |
| `alembic revision --autogenerate -m "说明"` | 按模型差异生成迁移 |
| `alembic upgrade head` | 升到最新 |
| `alembic upgrade +1` | 前进一步 |
| `alembic downgrade -1` | 回退一步 |
| `alembic downgrade base` | 全部回退 |
| `alembic stamp head` | 只记录版本，不执行 DDL |
| `alembic upgrade head --sql` | 只输出 SQL，不连库（离线模式） |

## 8. 排错

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| `UnicodeDecodeError: 'gbk' codec can't decode` | `alembic.ini` 里有中文，Alembic 用系统 locale 读配置 | 这个文件**必须纯 ASCII**，注释也用英文 |
| `Table 'xxx' already exists` | 表已存在还执行初始迁移 | 用 `alembic stamp head` 代替 `upgrade` |
| autogenerate 生成一堆 `DROP TABLE` | 库里有未建模的表 | 加 `include_object` |
| `alembic check` 报 comment 差异 | 模型里的 `comment` 与库里不一致 | 对齐，或删掉模型的 comment |
| `Can't locate revision identified by 'xxx'` | 本地版本文件被删了 | 检查 `migrations/versions/`，必要时 `alembic stamp` 修正 |

## 9. 两个常问的问题

**Q：`alembic stamp head` 和 `alembic upgrade head` 有什么区别？**

`upgrade` 会**执行** DDL；`stamp` 只往 `alembic_version` 表写一条版本号，**不执行任何 DDL**。

用在「表已经存在（手工建的、或者从别的库导的），但我想让 Alembic 接管后续变更」的场景。

**Q：多人协作时迁移文件冲突怎么办？**

每个迁移文件有唯一的 `revision` 哈希和 `down_revision` 指向父版本。两个人同时从同一版本分叉，就会出现「两个 head」。

解决：`alembic merge -m "merge branches" <rev1> <rev2>` 生成一个合并版本，把两条线接回来。预防办法是提交前先 `alembic history` 确认自己是接在最新的 head 上。
