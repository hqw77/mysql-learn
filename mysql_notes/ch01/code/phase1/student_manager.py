import os

import pymysql
from pymysql.cursors import DictCursor

# 1. 建立数据库连接（密码从环境变量读取,不要把密码写进代码）
def get_conn():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),  # 先 export MYSQL_PASSWORD=你的密码
        database=os.getenv("MYSQL_DATABASE", "learn_mysql"),
        charset="utf8mb4"
    )

def show_menu():
    print("\n" + "="*30)
    print("📚 学生管理系统")
    print("1. 录入学生")
    print("2. 查看所有学生")
    print("3. 修改分数")
    print("4. 删除学生")
    print("5. 退出")
    print("="*30)

def main():
    conn = get_conn()
    
    # 使用 DictCursor,让查询结果变成字典
    with conn.cursor(cursor=DictCursor) as cur:
        
        while True:
            show_menu()
            choice = input("请选择操作 (1-5): ").strip()

            # 1. 录入学生
            if choice == '1':
                name = input("请输入学生姓名: ").strip()
                if not name:
                    print("❌ 姓名不能为空！")
                    continue
                    
                try:
                    age = int(input("请输入学生年龄: "))
                    score = float(input("请输入学生分数: "))
                except ValueError:
                    print("❌ 年龄必须是整数,分数必须是数字！录入取消。")
                    continue

                # 使用 %s 占位符防止 SQL 注入
                sql = "INSERT INTO students (name, age, score) VALUES (%s, %s, %s)"
                cur.execute(sql, (name, age, score))
                conn.commit() # ⚠️ 千万别忘了 commit
                print(f"✅ 成功录入学生：{name}")

            # 2. 查看所有学生
            elif choice == '2':
                cur.execute("SELECT id, name, age, score FROM students ORDER BY id")
                students = cur.fetchall()
                
                if not students:
                    print("📭 当前系统里没有学生数据。")
                else:
                    print("\n" + "-"*45)
                    # 使用 f-string 对齐打印,<4 表示左对齐占4位
                    print(f"{'ID':<4} | {'姓名':<10} | {'年龄':<4} | {'分数':<6}")
                    print("-" * 45)
                    for stu in students:
                        # 因为用了 DictCursor,可以用 stu['name'] 这样取值
                        print(f"{stu['id']:<4} | {stu['name']:<10} | {stu['age']:<6} | {stu['score']:<8}")
                    print("-" * 45)

            # 3. 修改分数
            elif choice == '3':
                name = input("请输入要修改的学生姓名: ").strip()
                try:
                    new_score = float(input("请输入新的分数: "))
                except ValueError:
                    print("❌ 分数必须是数字！")
                    continue

                sql = "UPDATE students SET score = %s WHERE name = %s"
                affected_rows = cur.execute(sql, (new_score, name))
                conn.commit()
                
                if affected_rows > 0:
                    print(f"✅ 成功将 {name} 的分数修改为 {new_score}")
                else:
                    print(f"⚠️ 没有找到名叫 {name} 的学生。")

            # 4. 删除学生
            elif choice == '4':
                name = input("请输入要删除的学生姓名: ").strip()
                
                # 先查一下有没有这个人,避免误删或删空
                cur.execute("SELECT id FROM students WHERE name = %s", (name,))
                if not cur.fetchone():
                    print(f"⚠️ 没有找到名叫 {name} 的学生。")
                    continue

                sql = "DELETE FROM students WHERE name = %s"
                cur.execute(sql, (name,))
                conn.commit()
                print(f"🗑️ 成功删除学生：{name}")

            # 5. 退出
            elif choice == '5':
                print("👋 退出系统,再见！")
                break
            
            else:
                print("❌ 无效的选择,请输入 1-5 之间的数字。")

    # 退出循环后关闭连接
    conn.close()

if __name__ == "__main__":
    main()