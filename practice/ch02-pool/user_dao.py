"""用户管理 DAO：功能与 legacy 版一致，区别只在连接从池里借。

每借必还：conn.close() 对池连接而言是归还，不是断开。
"""

from pymysql.cursors import DictCursor

from pool import get_conn


class UserDAO:
    def add_user(self, username: str, password: str, age: int, email: str) -> int:
        sql = "INSERT INTO user(username, password, age, email) VALUES (%s, %s, %s, %s)"
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (username, password, age, email))
                conn.commit()
                return cur.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()          # 归还连接，不是断开

    def get_user(self, uid: int) -> dict | None:
        conn = get_conn()
        try:
            with conn.cursor(DictCursor) as cur:
                cur.execute("SELECT id, username, age, email, created_at FROM user WHERE id = %s", (uid,))
                return cur.fetchone()
        finally:
            conn.close()

    def list_users(self, limit: int = 10) -> list[dict]:
        conn = get_conn()
        try:
            with conn.cursor(DictCursor) as cur:
                cur.execute(
                    "SELECT id, username, age, email, created_at FROM user ORDER BY id DESC LIMIT %s",
                    (limit,),
                )
                return list(cur.fetchall())
        finally:
            conn.close()
