"""第五章 · 案例 2：多对多 —— 用户和角色。

学到什么：
    多对多必须靠中间表（user_roles）。ORM 用 secondary= 指定中间表，
    然后就能直接 user.roles.append(role) / remove(role)，中间表自动维护。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch05/code/02_many_to_many.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import delete, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Role, User, user_roles  # noqa: E402


def show(title: str) -> None:
    print(f"\n--- {title} ---")


if __name__ == "__main__":
    with SessionLocal() as db:
        show("① 库里有哪几个角色")
        for r in db.scalars(select(Role)):
            print("   ", r, "-", r.description)

        show("② 给张三加两个角色")
        user = db.get(User, 1)
        admin = db.scalar(select(Role).where(Role.name == "admin"))
        editor = db.scalar(select(Role).where(Role.name == "editor"))

        user.roles.append(admin)
        user.roles.append(editor)
        db.commit()                          # 💡 中间表由 ORM 自动写
        print("    张三现在的角色:", [r.name for r in user.roles])

        show("③ 反查：哪些用户有 admin 角色")
        for u in admin.users:
            print("   ", u.username)

        show("④ 撤销一个角色")
        user.roles.remove(editor)
        db.commit()
        print("    张三现在的角色:", [r.name for r in user.roles])

        show("⑤ 直接看中间表")
        rows = db.execute(select(user_roles)).all()
        for row in rows:
            print("    user_id =", row.user_id, " role_id =", row.role_id)

        show("⑥ 清理：把本次加的关联删掉，库恢复原样")
        db.execute(delete(user_roles).where(user_roles.c.user_id == 1))
        db.commit()
        print("    已清理")
