"""第三章 · 最小闭环：定义 Base → 定义 Model → 建 Engine → 开 Session → 查一条数据。

这个文件和 app/ 里的工程化版本是同一件事的两种形态：
    practice/ch03/mini_orm.py   ← 30 行，一个文件，看懂原理
    app/models/user.py          ← 分层版，看工程怎么写
对照读，进步最快。

运行：
    export MYSQL_PASSWORD=你的密码
    python practice/ch03/mini_orm.py
"""

import os
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, create_engine, select
from sqlalchemy.dialects.mysql import INTEGER, TINYINT  # ⚠️ 别用 sqlalchemy.INTEGER，它不认 unsigned
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# ① Engine：进程级唯一，内部自带连接池
engine = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}"
    f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
    f"/{os.getenv('MYSQL_DATABASE', 'learn_mysql')}?charset=utf8mb4",
    # 💡 想看它生成的 SQL 就把下面这行打开
    echo=False,
)


# ② Base：所有模型的基类，持有 metadata
class Base(DeclarativeBase):
    pass


# ③ Model：一个类 = 一张表，一个属性 = 一列
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_deleted: Mapped[bool] = mapped_column(TINYINT(1))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} balance={self.balance}>"


if __name__ == "__main__":
    # ④ Session：一次业务操作的工作单元
    with Session(engine) as session:
        # 按主键查，查不到返回 None，不抛异常
        user = session.get(User, 1)
        print("按主键查：", user)

        # 全表扫一遍，看看 ORM 把每行都变成了对象
        print("全部用户：")
        for u in session.scalars(select(User).limit(5)):
            print("  ", u)
