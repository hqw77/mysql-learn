import os

import pymysql
from pymysql.cursors import DictCursor

conn = pymysql.connect(
    host="localhost", user="root", password=os.getenv("MYSQL_PASSWORD", ""),
    database="learn_mysql", charset="utf8mb4"
)

def query_subquery():
    with conn.cursor(cursor=DictCursor) as cur:
        # 把刚才的嵌套子查询直接放进 Python 字符串里
        sql = """
        SELECT username FROM users 
        WHERE id IN (
            SELECT user_id FROM orders 
            WHERE id IN (
                SELECT order_id FROM order_items WHERE product_id = 1
            )
        );
        """
        cur.execute(sql)
        results = cur.fetchall()
        
        print("--- 购买过机械键盘的用户 ---")
        for row in results:
            print(row['username'])

try:
    query_subquery()
finally:
    conn.close()