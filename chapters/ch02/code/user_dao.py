from pool import get_conn

def get_user_by_id(user_id):
    """查询单个用户"""
    conn = get_conn()  # 借连接
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, balance FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()
    finally:
        conn.close()   # 归还连接（不是销毁！）

def create_user(username, phone, balance=0.00):
    """插入新用户"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, phone, balance) VALUES (%s, %s, %s)",
                (username, phone, balance)
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()