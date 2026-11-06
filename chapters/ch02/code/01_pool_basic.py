"""案例 1：连接池能借能还,而且借到的还是同一条物理连接。

学到什么：
    connection() 是「借」,close() 是「还」——池子里的连接从头到尾没有断过。
    三次借还拿到同一个 CONNECTION_ID(),说明省掉了三次 TCP 握手和认证。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch02/code/01_pool_basic.py
"""

from pool import MAX_CONNECTIONS, close_pool, get_conn


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    show("① 借一条连接,查一句")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            print("    查询结果:", cur.fetchone())
    finally:
        conn.close()          # ⚠️ 不 close 就是泄漏,池子迟早被借空

    show("② 连续借三次,看连接 id 是否复用")
    ids = []
    for _ in range(3):
        c = get_conn()
        try:
            with c.cursor() as cur:
                cur.execute("SELECT CONNECTION_ID()")
                ids.append(cur.fetchone()[0])
        finally:
            c.close()
    print("    三次借到的连接 id:", ids)
    print(f"    去重后只有 {len(set(ids))} 个 —— 正好是池子预建的连接数,没有新建")

    show("③ 池子的上限")
    print(f"    maxconnections = {MAX_CONNECTIONS}")
    print("    刚才 3 次借还都归还了,池子没有泄漏")

    close_pool()
    print("\n池子已关闭。")
