import os

import pymysql

conn = pymysql.connect(
    host="localhost", user="root", password=os.getenv("MYSQL_PASSWORD", ""),
    database="learn_mysql", charset="utf8mb4"
)

def transfer_money(from_user, to_user, amount):
    try:
        with conn.cursor() as cur:
            # 1. 开启事务 (PyMySQL 默认不自动提交,执行 DML 语句即开启事务)
            # 也可以显式执行 cur.execute("BEGIN;")
            
            print(f"开始转账：{from_user} -> {to_user} ￥{amount}")
            # 步骤 1：扣钱
            cur.execute("UPDATE users SET balance = balance - %s WHERE username = %s", (amount, from_user))
            # 步骤 2：加钱
            cur.execute("UPDATE users SET balance = balance + %s WHERE username = %s", (amount, to_user))
            
            # 模拟程序崩溃（主动抛出异常）
            # 把下面这行注释掉,转账就会成功。
            raise Exception("💥 服务器突然断电,转账中断！") 
            
            # 如果上面没报错,提交事务
            conn.commit()
            print("✅ 转账成功！")
            
    except Exception as e:
        # 如果中途报错,回滚事务（撤销所有操作）
        conn.rollback()
        print(f"❌ 转账失败,已回滚。错误信息: {e}")
    finally:
        conn.close()

# 测试转账：把刚才造数据里的李四的 500 转 100 给王五
transfer_money('李四', '王五', 100)


