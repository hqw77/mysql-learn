import os

import pymysql

conn = pymysql.connect(
    host="localhost", user="root", password=os.getenv("MYSQL_PASSWORD", ""),
    database="learn_mysql", charset="utf8mb4"
)

def show_tables():
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES;")
        tables = cur.fetchall()
        print("=== 当前数据库中的表 ===")
        for t in tables:
            print(f"- {t[0]}")

try:
    show_tables()
finally:
    conn.close()