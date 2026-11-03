import os

import pymysql

try:
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),  # 从环境变量读取，不要把密码写进代码
        charset="utf8mb4",
    )
    print("✅ 成功连接到 MySQL 服务器！\n")

    with conn.cursor() as cur:
        cur.execute("SELECT VERSION();")
        version = cur.fetchone()
        print(f"🔹 MySQL 版本: {version[0]}\n")

        cur.execute("SHOW DATABASES;")
        print("🔹 当前系统自带的数据库:")
        for row in cur.fetchall():
            print(f"  - {row[0]}")

except pymysql.err.OperationalError as e:
    print("❌ 连接失败，请检查服务是否启动、密码是否正确")
    print(f"错误详情: {e}")
finally:
    if 'conn' in locals() and conn.open:
        conn.close()
        print("\n🔒 数据库连接已安全关闭。")