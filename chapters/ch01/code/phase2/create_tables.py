import os

import pymysql

conn = pymysql.connect(
    host="localhost", user="root", password=os.getenv("MYSQL_PASSWORD", ""),
    database="learn_mysql", charset="utf8mb4"
)

def run_ddl():
    with conn.cursor() as cur:
        create_sql = """
        CREATE TABLE IF NOT EXISTS tags (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            tag_name VARCHAR(50) NOT NULL UNIQUE COMMENT '标签名',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        cur.execute(create_sql)
        conn.commit()
        print("✅ tags 表创建成功！")

        cur.execute("DESC tags;")
        print("\n--- tags 表结构 ---")
        for col in cur.fetchall():
            print(col)

try:
    run_ddl()
finally:
    conn.close()