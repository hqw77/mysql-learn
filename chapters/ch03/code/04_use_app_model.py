"""案例 4：用 app/ 里那份「工程版」模型,查同一条数据。

学到什么：
    同一个 User,写在单个脚本里和写在 app/models/ 里,
    对使用者来说调用方式几乎一样——这就是"好的抽象"。

怎么跑（必须在仓库根目录执行）：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch03/code/04_use_app_model.py

和案例 1 的关系：
    案例 1 的 User 是本地定义的；
    这里的 User 来自 app.models,背后连着 app/db/ 的 Engine 和 Session。
    数据完全一样,只是模型放在哪、谁来管连接的区别。
"""

import sys
from pathlib import Path

# 让脚本能从仓库根目录 import app 包
# 文件在 chapters/ch03/code/ 下,往上退三级才是仓库根
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

if __name__ == "__main__":
    print("模型来自：app.models.user.User")
    print("引擎来自：app.db.engine.engine")
    print("会话来自：app.db.session.SessionLocal")
    print()

    with SessionLocal() as db:
        print("【1】按主键查（和案例 1 写法一模一样）")
        user = db.get(User, 1)
        print("   ", user)

        print()
        print("【2】查全部")
        for u in db.scalars(select(User)):
            print("   ", u)

        print()
        print("【3】和案例 1 对比：差别只在 import")
        print("    案例1:  class User(Base) 写在脚本里")
        print("    案例4:  from app.models import User")
        print("    → 业务代码不需要知道引擎和会话从哪来,这就是分层")
