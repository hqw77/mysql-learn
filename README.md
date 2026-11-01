# mysql-learning

MySQL 学习记录：从环境搭建到单表 CRUD，每一步都留下笔记、SQL 和可运行的 Python 代码。

## 目录结构

```
mysql-learning/
├── notes/       # 学习笔记（Markdown，按阶段编号）
├── sql/         # 纯 SQL 练习脚本
├── phase0/      # 阶段 0：环境搭建与连通性验证
├── phase1/      # 阶段 1：单表 CRUD 与基础查询
└── requirements.txt
```

## 进度

| 阶段 | 主题 | 笔记 | 代码 |
| --- | --- | --- | --- |
| 0 | 环境搭建与连通 | [notes/阶段0 -- 环境搭建与连通.md](notes/阶段0%20--%20环境搭建与连通.md) | `phase0/check_connection.py` |
| 1 | 单表 CRUD 与基础查询 | [notes/阶段1 -- 单表 CRUD 与基础查询.md](notes/阶段1%20--%20单表%20CRUD%20与基础查询.md) | `phase1/crud_basic.py`、`phase1/student_manager.py`、`sql/01-crud.sql` |

## 环境准备

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# .venv\Scripts\activate         # Windows CMD / PowerShell

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置数据库连接（密码不要写进代码）
cp .env.example .env             # 然后编辑 .env 填入真实密码
```

代码通过环境变量读取连接信息，运行前先让变量生效：

```bash
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=你的密码
export MYSQL_DATABASE=learn_mysql
```

## 运行

```bash
python phase0/check_connection.py    # 验证能否连通 MySQL
python phase1/crud_basic.py          # 增删改查演示
python phase1/student_manager.py     # 学生管理 CLI
```

## 说明

- 环境是 Windows + MySQL 8.0.42（zip 解压版），服务名 `MySQL`。
- `.venv/` 和 `.env` 已加入 `.gitignore`，不会被提交。
- 所有密码一律通过环境变量传入，仓库中不保存任何凭据。
