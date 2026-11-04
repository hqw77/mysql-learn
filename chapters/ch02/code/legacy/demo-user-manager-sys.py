import os

import pymysql
from pymysql.cursors import DictCursor


class UserDB:
    def __init__(self):
        self.conn = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password=os.getenv('MYSQL_PASSWORD', ''),
            database='test_db',
            charset='utf8mb4',
        )

    def add_user(self, username, password, age, email):
        sql = "INSERT INTO user(username,password,age,email) VALUES (%s,%s,%s,%s)"
        with self.conn.cursor(DictCursor) as cur:
            cur.execute(sql,(username,password,age,email))
            self.conn.commit()
            return cur.lastrowid

    def get_user(self,uid):
        sql = "SELECT * FROM user WHERE id=%s"
        with self.conn.cursor(DictCursor) as cur:
            cur.execute(sql,(uid,))
            return cur.fetchone()

    def close(self):
        self.conn.close()

if __name__ == '__main__':
    db = UserDB()
    newid = db.add_user("小明", "123456", 18, "xm@qq.com")
    print("新增id", newid)
    print(db.get_user(newid))
    db.close()