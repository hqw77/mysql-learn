**学习方向：Python 后端开发 / AI 应用开发工程师**

**技术版本：Python 3、MySQL 8、SQLAlchemy 2.x、FastAPI**

## 一、学习目标
通过本教程,掌握 Python 操作 MySQL 的进阶开发能力,能够独立完成一个具有实际开发价值的用户管理系统。

最终达到：

1. 熟练使用 PyMySQL 操作 MySQL。
2. 理解数据库连接池的原理和使用方法。
3. 掌握 SQLAlchemy ORM 的基本使用和进阶操作。
4. 理解数据库事务、索引、锁和 SQL 优化。
5. 掌握 FastAPI 与 MySQL 的整合。
6. 能够独立设计数据库模型和开发后端 API。
7. 能够回答 Python 后端开发相关数据库面试题。

## 二、学习章节
### 第一章：MySQL 进阶基础
+ 数据库索引及 B+Tree 原理
+ 普通索引、唯一索引、主键索引
+ EXPLAIN 执行计划
+ SQL 查询优化
+ INNER JOIN、LEFT JOIN
+ 一对一、一对多、多对多
+ 事务 ACID 特性
+ COMMIT 和 ROLLBACK
+ 行锁、表锁
+ MySQL 隔离级别

实战：设计用户表、角色表和订单表。

### 第二章：Python 数据库连接池
+ 什么是数据库连接
+ 为什么需要连接池
+ 连接池的工作原理
+ DBUtils 安装
+ PooledDB 参数详解
+ 获取连接和归还连接
+ 连接池异常处理
+ 多线程并发访问数据库

实战：将原有 PyMySQL 用户管理系统改造成连接池版本。

### 第三章：SQLAlchemy ORM 基础
+ 什么是 ORM
+ ORM 与原生 SQL 的区别
+ SQLAlchemy 架构
+ Engine
+ DeclarativeBase
+ Model
+ mapped_column
+ Session
+ 数据库连接字符串
+ create_all 创建数据表

实战：使用 SQLAlchemy 创建 User 模型。

### 第四章：SQLAlchemy ORM CRUD
+ session.add()
+ session.get()
+ select()
+ session.execute()
+ session.delete()
+ session.commit()
+ session.rollback()
+ filter 和 where
+ order_by 排序
+ limit 和 offset 分页
+ 条件查询
+ 批量操作

实战：使用 ORM 完整重写用户管理系统。

### 第五章：SQLAlchemy 进阶
+ relationship 关系映射
+ ForeignKey 外键
+ 一对多关系
+ 多对多关系
+ 懒加载和预加载
+ Session 生命周期
+ 事务管理
+ 连接池配置
+ 数据库异常处理
+ 数据库迁移 Alembic

实战：实现用户、角色、权限之间的关联。

### 第六章：FastAPI + MySQL
+ FastAPI 基础
+ 路由和请求方法
+ Pydantic 数据模型
+ 数据库依赖注入
+ Session 管理
+ GET、POST、PUT、DELETE
+ HTTP 状态码
+ 异常处理
+ API 参数校验
+ 分页接口

实战：将用户管理系统改造成 RESTful API。

### 第七章：完整项目实战
项目名称：用户管理系统。

项目功能：

+ 用户注册
+ 用户登录
+ 密码安全存储
+ 用户信息管理
+ 用户查询
+ 用户删除
+ 角色管理
+ 权限关联
+ 分页查询
+ 数据库事务
+ API 接口开发
+ 异常处理

项目要求：

+ 采用分层架构
+ 配置文件与业务代码分离
+ 数据库连接统一管理
+ 使用 SQLAlchemy ORM
+ 使用 FastAPI
+ 编写基础自动化测试
+ 编写 README 项目说明

### 第八章：面试题与项目复盘
重点面试题：

1. 什么是数据库连接池？为什么需要它？
2. PyMySQL 和 SQLAlchemy 有什么区别？
3. 什么是 ORM？
4. SQLAlchemy 的 Engine 和 Session 有什么区别？
5. Session 和数据库连接是什么关系？
6. SQLAlchemy 如何管理事务？
7. 数据库连接池参数如何设置？
8. 什么是数据库索引？
9. 什么是事务的 ACID 特性？
10. 如何优化慢 SQL？
11. 如何解决数据库并发访问问题？
12. FastAPI 如何管理数据库 Session？

## 三、统一教学方式
每章必须包含：

1. 学习目标
2. 基础概念
3. 原理讲解
4. 架构图或流程图
5. 环境准备
6. 完整代码示例
7. 逐行代码解释
8. 实战项目
9. 动手练习
10. 常见错误排查
11. 高频面试题
12. 本章知识总结

## 四、项目目录规范

本仓库实际采用的划分（与最初设想相比,工程代码收进 `app/` 包,章节材料按章归档）：

```plain
mysql-learning/
├── chapters/                 # 学习区：每章一个目录
│   ├── ch01/
│   │   ├── notes/            # 笔记（.md）
│   │   ├── code/             # 代码（.py）
│   │   └── sql/              # 纯 SQL 脚本（有才建）
│   ├── ch02/ ... chNN/
│   └── extras/               # 番外专题
├── app/                      # 工程区：最终项目
│   ├── main.py
│   ├── deps.py
│   ├── core/                 # config.py / exceptions.py
│   ├── db/                   # base.py / engine.py / session.py
│   ├── models/               # ORM 实体
│   ├── schemas/              # Pydantic 模型
│   ├── services/             # 业务逻辑
│   └── routers/              # HTTP 路由
├── migrations/               # Alembic 迁移
├── docs/                     # 架构、规划、文档规范
├── requirements.txt
└── README.md
```

## 五、学习要求
+ 每章先理解原理,再动手写代码。
+ 所有代码必须能够独立运行。
+ 不跳过关键代码和参数解释。
+ 每章完成后进行练习和知识检查。
+ 遇到报错,先学会阅读 Traceback。
+ 最终能够不依赖教程独立完成项目。

**最终目标：从会使用 PyMySQL 执行 CRUD,成长为能够使用 Python、MySQL、SQLAlchemy 和 FastAPI 独立开发后端业务系统的开发者。**

