## 1. 准备工作：建库建表
首先，我们得有一张表用来练手。打开终端，确保你连上了 MySQL（`mysql -u root -p`），或者在 VS Code 的 Database Client 插件里执行以下 SQL。

```plain
-- 创建数据库（如果不存在）并指定字符集
CREATE DATABASE IF NOT EXISTS learn_mysql DEFAULT CHARACTER SET utf8mb4;

-- 切换到该数据库
USE learn_mysql;

-- 创建学生表
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,        -- 自增主键
    name VARCHAR(50) NOT NULL,                -- 姓名，不能为空
    age INT DEFAULT 18,                       -- 年龄，默认18
    score DECIMAL(5, 2) DEFAULT 0.00,         -- 分数，保留两位小数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，自动填入当前时间
);
```

_(建好后，可以在终端敲 _`_DESC students;_`_ 看看表结构)_

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793544829453-8084a806-3acf-4df7-bf85-af6f4d9b3e5d.png)

## 2. 核心 SQL 语法（要背熟）
打开你项目里的 `sql/01-crud.sql`，把这些基础语法敲一遍并执行：

**增 (INSERT)**

```plain
-- 插入单条（指定所有列）
INSERT INTO students (name, age, score) VALUES ('张三', 20, 85.5);
-- 插入单条（不指定列，必须按表结构顺序给全）
INSERT INTO students VALUES (NULL, '李四', 19, 92.0, NOW());
-- 批量插入（性能更好，推荐用）
INSERT INTO students (name, age, score) VALUES ('王五', 21, 78.0), ('赵六', 22, 88.5);
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793544846632-f0a7a48f-1a12-47fb-b677-8c68158030f0.png)

**查 (SELECT)**

```plain
-- 查所有
SELECT * FROM students;
-- 条件查（找分数大于 80 的）
SELECT name, score FROM students WHERE score > 80;
-- 排序 + 分页（按分数降序，取前 2 个）
SELECT * FROM students ORDER BY score DESC LIMIT 2;
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793544946568-ae5fdeb6-013c-4c7b-bd59-21bbb0e43e3c.png)

**改 (UPDATE)**

```plain
-- 把张三的分数改成 90（一定要带 WHERE，否则全表都被改）
UPDATE students SET score = 90.0 WHERE name = '张三';
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793544984675-6376ec4a-3fe2-4284-acb7-58faaebe8652.png)

**删 (DELETE)**

```plain
-- 删除名字叫李四的记录（同样一定要带 WHERE）
DELETE FROM students WHERE name = '李四';
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793545002427-6111de69-118d-4f7e-968b-11e5b7ea082f.png)

## 3. Python 实战（PyMySQL）
现在，打开 `chapters/ch01/code/phase1/crud_basics.py`，开始写真正的后端代码。

```plain
import pymysql
from pymysql.cursors import DictCursor

# 1. 建立连接 (加上 autocommit=True 可以省去手动 commit 的麻烦)
# 但为了学习事务，我们这里不加，手动提交
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="你的root密码", # <--- 改成你的密码
    database="learn_mysql",
    charset="utf8mb4"
)

def run_sql():
    # 使用 DictCursor，让查询结果变为字典格式
    with conn.cursor(cursor=DictCursor) as cur:
        
        print("--- 1. 增 (INSERT) ---")
        # 使用 %s 作为占位符（这是 PyMySQL 的标准写法，不管是数字还是字符串都用 %s，防 SQL 注入）
        insert_sql = "INSERT INTO students (name, age, score) VALUES (%s, %s, %s)"
        cur.execute(insert_sql, ('孙七', 23, 95.5))
        
        # 必须 commit，数据才会真正写入数据库
        conn.commit()
        print(f"插入了 1 条数据，新数据的 ID 是: {cur.lastrowid}\n")

        print("--- 2. 查 (SELECT) ---")
        cur.execute("SELECT * FROM students")
        # fetchall() 拿到所有结果，结果是一个列表，里面是字典
        students = cur.fetchall()
        for stu in students:
            print(f"ID: {stu['id']}, 姓名: {stu['name']}, 分数: {stu['score']}")
        print("")

        print("--- 3. 改 (UPDATE) ---")
        update_sql = "UPDATE students SET score = %s WHERE name = %s"
        affected_rows = cur.execute(update_sql, (100.0, '孙七'))
        conn.commit()
        print(f"更新了 {affected_rows} 条数据\n")

        print("--- 4. 删 (DELETE) ---")
        delete_sql = "DELETE FROM students WHERE name = %s"
        affected_rows = cur.execute(delete_sql, ('孙七',))
        conn.commit()
        print(f"删除了 {affected_rows} 条数据\n")

# 执行函数并妥善关闭连接
try:
    run_sql()
finally:
    conn.close()
    print("🔒 数据库连接已关闭。")
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793545223367-85e39a87-1c8b-4a8c-afe4-286d72768481.png)

## 4. Python + PyMySQL 核心操作
### 4.1 默认元组游标 vs 字典游标
+ **默认游标**：`fetchone()` 返回 `(1, '张三', 20, 85.5, datetime.datetime(...))`。取值靠下标，非常不直观。
+ **字典游标（推荐）**：`fetchall()` 返回 `[{'id': 1, 'name': '张三', 'age': 20, ...}]`。取值靠键名（`stu['name']`），代码可读性极强。

### 4.2 防 SQL 注入（占位符）
无论传入的是字符串、数字还是日期，PyMySQL 的占位符统一使用 `%s`（不要加引号）。

```plain
# 正确写法
cur.execute("SELECT * FROM students WHERE age = %s AND score > %s", (20, 80))

# 错误写法（会被当成字符串拼接，有 SQL 注入风险）
cur.execute(f"SELECT * FROM students WHERE age = {age}")
```

### 4.3 事务提交（`commit`）
在 PyMySQL 中，**默认是不自动提交事务的**。

+ 执行 `INSERT`、`UPDATE`、`DELETE` 后，**必须调用 **`conn.commit()`，数据才会真正写入数据库。
+ 如果发生了异常，可以调用 `conn.rollback()` 撤销。

### 4.4 获取自增 ID
插入一条数据后，可以通过 `cur.lastrowid` 获取刚插入那行数据的主键 ID。

## 5. 阶段 1 进阶任务（验收作业）
光是跑通上面的代码不够，你现在需要独立完成以下任务。

打开 `chapters/ch01/code/phase1/student_manager.py`，用 PyMySQL 写一个**控制台交互版的学生管理系统**：

1. 程序启动时，给用户显示菜单（1. 录入学生；2. 查看所有学生；3. 修改分数；4. 删除学生；5. 退出）。
2. 用户选择 1，提示用户输入姓名、年龄、分数，用代码插入数据库。
3. 用户选择 2，用 DictCursor 查出来，优雅地打印成表格。
4. 用户选择 3，提示输入学生名字和新分数，执行 UPDATE。
5. 用户选择 4，提示输入学生名字，执行 DELETE。
6. 用 `while True:` 让程序一直循环，直到用户选择 5 才退出并关闭连接。

_(提示：每次增删改之后，千万不要忘记 _`_conn.commit()_`_)_

```plain
import pymysql
from pymysql.cursors import DictCursor

# 1. 建立数据库连接（记得改成你真实的密码）
def get_conn():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="你的root密码",  # <--- 换成你的密码
        database="learn_mysql",
        charset="utf8mb4"
    )

def show_menu():
    print("\n" + "="*30)
    print("📚 学生管理系统")
    print("1. 录入学生")
    print("2. 查看所有学生")
    print("3. 修改分数")
    print("4. 删除学生")
    print("5. 退出")
    print("="*30)

def main():
    conn = get_conn()
    
    # 使用 DictCursor，让查询结果变成字典
    with conn.cursor(cursor=DictCursor) as cur:
        
        while True:
            show_menu()
            choice = input("请选择操作 (1-5): ").strip()

            # 1. 录入学生
            if choice == '1':
                name = input("请输入学生姓名: ").strip()
                if not name:
                    print("❌ 姓名不能为空！")
                    continue
                    
                try:
                    age = int(input("请输入学生年龄: "))
                    score = float(input("请输入学生分数: "))
                except ValueError:
                    print("❌ 年龄必须是整数，分数必须是数字！录入取消。")
                    continue

                # 使用 %s 占位符防止 SQL 注入
                sql = "INSERT INTO students (name, age, score) VALUES (%s, %s, %s)"
                cur.execute(sql, (name, age, score))
                conn.commit() # ⚠️ 千万别忘了 commit
                print(f"✅ 成功录入学生：{name}")

            # 2. 查看所有学生
            elif choice == '2':
                cur.execute("SELECT id, name, age, score FROM students ORDER BY id")
                students = cur.fetchall()
                
                if not students:
                    print("📭 当前系统里没有学生数据。")
                else:
                    print("\n" + "-"*45)
                    # 使用 f-string 对齐打印，<4 表示左对齐占4位
                    print(f"{'ID':<4} | {'姓名':<10} | {'年龄':<4} | {'分数':<6}")
                    print("-" * 45)
                    for stu in students:
                        # 因为用了 DictCursor，可以用 stu['name'] 这样取值
                        print(f"{stu['id']:<4} | {stu['name']:<10} | {stu['age']:<6} | {stu['score']:<8}")
                    print("-" * 45)

            # 3. 修改分数
            elif choice == '3':
                name = input("请输入要修改的学生姓名: ").strip()
                try:
                    new_score = float(input("请输入新的分数: "))
                except ValueError:
                    print("❌ 分数必须是数字！")
                    continue

                sql = "UPDATE students SET score = %s WHERE name = %s"
                affected_rows = cur.execute(sql, (new_score, name))
                conn.commit()
                
                if affected_rows > 0:
                    print(f"✅ 成功将 {name} 的分数修改为 {new_score}")
                else:
                    print(f"⚠️ 没有找到名叫 {name} 的学生。")

            # 4. 删除学生
            elif choice == '4':
                name = input("请输入要删除的学生姓名: ").strip()
                
                # 先查一下有没有这个人，避免误删或删空
                cur.execute("SELECT id FROM students WHERE name = %s", (name,))
                if not cur.fetchone():
                    print(f"⚠️ 没有找到名叫 {name} 的学生。")
                    continue

                sql = "DELETE FROM students WHERE name = %s"
                cur.execute(sql, (name,))
                conn.commit()
                print(f"🗑️ 成功删除学生：{name}")

            # 5. 退出
            elif choice == '5':
                print("👋 退出系统，再见！")
                break
            
            else:
                print("❌ 无效的选择，请输入 1-5 之间的数字。")

    # 退出循环后关闭连接
    conn.close()

if __name__ == "__main__":
    main()
```

![](https://cdn.nlark.com/yuque/0/2026/png/54927389/1793545421185-34905b38-b738-4baf-afd1-84f10773a49b.png)

## 6. 踩坑复盘记录
1. `mysql: command not found`：终端没识别到 MySQL 命令，需将 `bin` 路径加入系统环境变量并**重启 VS Code**。
2. `UnicodeEncodeError: 'latin-1' codec can't encode...`：PyMySQL 默认用拉丁编码处理密码，如果 root 密码里有中文就会报错。解决：在连接时加上 `charset="utf8mb4"`，或者将 root 密码改为纯英文/数字。
3. **查询结果是元组**：默认游标是元组，一定要用 `from pymysql.cursors import DictCursor` 配合 `conn.cursor(cursor=DictCursor)` 才能拿到字典格式。
4. **数据没保存**：`INSERT` / `UPDATE` / `DELETE` 执行完后，一定不要忘记 `conn.commit()`。

































