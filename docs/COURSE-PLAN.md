# 教程文档规划

> 这份文件回答三个问题：一共要写几篇、每篇写什么、按什么顺序写。
> 排版规范见 [DOC-PATTERN](DOC-PATTERN.md)。

## 0. 现状盘点

| 章 | 教程正文 | 篇幅 | 状态 |
| --- | --- | --- | --- |
| 第 1 章 | `chapters/ch01/notes/`（8 篇阶段笔记） | 2586 行 | 已有,形态是**学习笔记**不是教程 |
| 第 2 章 | `chapters/ch02/notes/Python 数据库连接池.md` | 175 行 | 完成 |
| 第 3 章 | `chapters/ch03/notes/SQLAlchemy ORM 基础.md` | 529 行 | 完成（偏长,下次注意） |
| 第 4~8 章 | — | — | 未开始 |

## 1. 全系列地图

| 章 | 标题 | 要解决的问题 | 篇幅预算 | 练习 | 工程增量 |
| --- | --- | --- | --- | --- | --- |
| 1 | MySQL 进阶基础 | SQL 怎么写对、写快 | 已有 | `chapters/ch01/code/` | — |
| 2 | Python 数据库连接池 | 连接为什么贵、怎么复用 | 175 ✅ | `chapters/ch02/code/` | — |
| 3 | SQLAlchemy ORM 基础 | ORM 是什么、第一条查询 | 400 | `chapters/ch03/code/` | `app/models/user.py` |
| 4 | SQLAlchemy ORM CRUD | 增删改查怎么写才不土 | 350 | `chapters/ch04/code/` | `app/services/` |
| 5 | SQLAlchemy 进阶 | 关系映射、事务、迁移 | 400 + 番外 | `chapters/ch05/code/` | `app/models/role.py` |
| 6 | FastAPI + MySQL | 把 ORM 暴露成 API | 380 | `chapters/ch06/code/` | `app/schemas/`、`app/routers/` |
| 7 | 完整项目实战 | 注册登录、权限、测试 | 450（或拆 2 篇） | — | 完整 `app/` + `tests/` |
| 8 | 面试题与复盘 | 把知识串成能说出口的话 | 150 | — | — |

> 篇幅预算是硬指标。第 3 章写了 529 行,读起来累——下次按预算收。

## 2. 正文与番外怎么切

**三条判定规则：**

| 规则 | 去正文 | 去番外 |
| --- | --- | --- |
| 主线能不能跑通这一步？ | 不能跑通就写不下去 → 正文 | 只是锦上添花 → 番外 |
| 是不是每章都要用？ | 常用 → 正文 | 特定场景 → 番外 |
| 会不会打断阅读节奏？ | 短 → 正文 | 一写就是千字 → 番外 |

**番外清单：**

| 编号 | 标题 | 来源 | 状态 |
| --- | --- | --- | --- |
| 01 | Alembic 数据库迁移 | 从第 3 章拆出 | ✅ 已写 |
| 02 | 关系映射详解（一对一 / 一对多 / 多对多 + N+1） | 第 5 章的备选下沉 | 待写 |
| 03 | Alembic 团队协作与版本冲突 | 第 5 章衍生 | 待写 |
| 04 | 连接池参数调优实录 | 第 2 章遗留的深入 | 待写 |
| 05 | Docker 一键起 MySQL | 环境篇 | 待写 |

## 3. 每章的固定交付物

一章写完,仓库里必须同时出现这 5 样,缺一样都不算完成：

```plain
① 教程正文      chapters/chNN/notes/<章名>.md
② 练习代码      chapters/chNN/code/xxx.py        ← 能独立跑,不依赖 app
③ 工程增量      app/...                     ← 从第 3 章开始的章才有
④ 索引更新      README.md 学习进度 + 笔记索引
⑤ 验收清单      正文末尾 4 条勾选项
```

## 4. 依赖关系与写作顺序

```plain
ch1 SQL 基础
 └─► ch2 连接池（依赖 ch1 的裸 SQL）
      └─► ch3 ORM 基础（依赖 ch2 的池概念）
           ├─► 番外01 Alembic（ch3 之后随时可读）
           └─► ch4 CRUD（依赖 ch3 的模型）
                └─► ch5 进阶（依赖 ch4 的 service 分层）
                     └─► ch6 API（依赖 ch5 的关系映射）
                          └─► ch7 项目（依赖 ch6 的路由与校验）
                               └─► ch8 复盘（依赖前 7 章全部）
```

**顺序不可乱**：第 5 章讲 `relationship`,前提是第 4 章已经有 `services/` 承接业务逻辑；第 6 章讲依赖注入,前提是第 5 章已经有可复用的 service。跳章写会得到一堆"暂时用不上"的代码。

## 5. 单章生产流程

```plain
① 我给「骨架 + Step 1 代码」
        ↓  你确认方向（跑通了吗、例子是不是你想学的）
② 我展开正文（按 DOC-PATTERN 的 7 节结构）
        ↓
③ 落 chapters/chNN/code 代码,真跑一遍,把真实输出贴进文档
        ↓
④ 更新 README 进度、必要时更新 ARCHITECTURE
        ↓  你验收（勾完 4 条清单）
⑤ commit + push
```

**第 ① 步是你的检查点**。方向不对就在这一步喊停,别等我写完 400 行。

## 6. 进度看板

| 章 | 正文 | 练习 | 工程 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | ✅ | ✅ | — | 完成 |
| 2 | ✅ | ✅ | — | 完成 |
| 3 | ✅ | ✅ | ✅ | 完成 |
| 4 | ✅ | ✅ | ✅ | 完成 |
| 5 | ✅ | ✅ | ✅ | 完成 |
| 6 | ✅ | ✅ | ✅ | 完成 |
| 7 | ⬜ | ⬜ | ⬜ | 未开始（当前停在第六章） |
| 8 | ⬜ | ⬜ | ⬜ | 未开始 |

**第四~六章工程增量**

| 章 | 新增文件 |
| --- | --- |
| 4 | `app/services/user_service.py`（业务逻辑与事务边界） |
| 5 | `app/models/order.py`、`app/models/role.py`、`migrations/versions/0002_add_roles.py` |
| 6 | `app/schemas/user.py`、`app/routers/users.py`,`main.py` 注册路由 |

## 7. 第三章的收口

第三章目前的状态：正文完成、`chapters/ch03/code/mini_orm.py` 可跑、`app/models/user.py` 已映射真实表、`alembic check` 无差异。

**验收清单（4 条,自测用）：**

- [ ] 不查资料能写出 Base / Model / engine / Session 四件套
- [ ] 能解释 `session.get(User, 1)` 和 `select(User).where(...)` 的区别
- [ ] 能说出赋相同值为什么不会发 UPDATE
- [ ] 能解释 `server_default` 和 `default` 生成的 DDL 差在哪

**如果还想在第三章多练,三个可选加练：**

| 加练 | 做什么 | 对应考点 |
| --- | --- | --- |
| A | 给 `mini_orm.py` 加一段"改余额 → 观察 dirty → rollback"的打印 | 脏检查、事务 |
| B | 用 `select()` 写"按用户名查",对比 `get()` 的差异 | 身份映射、N+1 |
| C | 给 `User` 加 `__repr__` 和工作状态属性,观察打印变化 | 模型定义 |

这三个加练都是 20 分钟内能做完的,做完第三章就算真的吃透了。
