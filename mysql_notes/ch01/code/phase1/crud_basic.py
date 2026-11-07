import os

import pymysql
from pymysql.cursors import DictCursor

# 1. 建立连接 (加上 autocommit=True 可以省去手动 commit 的麻烦)
# 但为了学习事务,我们这里不加,手动提交
conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST", "localhost"),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),  # 从环境变量读取,不要把密码写进代码
    database=os.getenv("MYSQL_DATABASE", "learn_mysql"),
    charset="utf8mb4"
)

def run_sql():
    # 使用 DictCursor,让查询结果变为字典格式
    with conn.cursor(cursor=DictCursor) as cur:
        
        print("--- 1. 增 (INSERT) ---")
        # 使用 %s 作为占位符（这是 PyMySQL 的标准写法,不管是数字还是字符串都用 %s,防 SQL 注入）
        insert_sql = "INSERT INTO students (name, age, score) VALUES (%s, %s, %s)"
        cur.execute(insert_sql, ('孙七', 23, 95.5))
        
        # 必须 commit,数据才会真正写入数据库
        conn.commit()
        print(f"插入了 1 条数据,新数据的 ID 是: {cur.lastrowid}\n")

        print("--- 2. 查 (SELECT) ---")
        cur.execute("SELECT * FROM students")
        # fetchall() 拿到所有结果,结果是一个列表,里面是字典
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