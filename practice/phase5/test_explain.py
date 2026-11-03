import os

import pymysql
from pymysql.cursors import DictCursor

conn = pymysql.connect(
    host="localhost", user="root", password=os.getenv("MYSQL_PASSWORD", ""),
    database="learn_mysql", charset="utf8mb4"
)

def check_explain():
    with conn.cursor(cursor=DictCursor) as cur:
        # 1. 查看当前 SQL 的执行计划
        print("=== 1. 无索引时的 EXPLAIN ===")
        cur.execute("EXPLAIN SELECT * FROM big_users WHERE age = 25")
        for row in cur.fetchall():
            print(f"type: {row['type']}, key: {row['key']}, rows: {row['rows']}")

        # 2. 加索引
        print("\n--- 给 age 添加索引 ---")
        cur.execute("CREATE INDEX idx_age ON big_users(age)")
        
        # 3. 再次查看执行计划
        print("\n=== 2. 加索引后的 EXPLAIN ===")
        cur.execute("EXPLAIN SELECT * FROM big_users WHERE age = 25")
        for row in cur.fetchall():
            print(f"type: {row['type']}, key: {row['key']}, rows: {row['rows']}")

try:
    check_explain()
finally:
    conn.close()