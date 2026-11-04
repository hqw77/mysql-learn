"""案例 1：最小闭环 —— 用 ORM 查出第一条数据。

学到什么：
    Engine / Base / Model / Session 四个对象各自的职责，
    以及 session.get() 拿回来的是对象，不是字典。

怎么跑：
    export MYSQL_PASSWORD=你的密码
    python chapters/ch03/code/01_first_query.py
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
    # 💡 想看它生成了什么 SQL，把 True 打开
    echo=False,
)


# ② Base：模型登记册，子类会自动注册到 Base.metadata
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
        print("【1】按主键查一条")
        user = session.get(User, 1)
        print("    返回值类型：", type(user).__name__)
        print("    对象本身   ：", user)
        print("    取属性     ：", user.username, "|", user.balance, "|", user.phone)

        print()
        print("【2】查不到时返回什么")
        missing = session.get(User, 999999)
        print("    session.get(User, 999999) ->", missing)
        print("    没有抛异常，只是 None")

        print()
        print("【3】把整张表取回来（每行都是一个对象）")
        for u in session.scalars(select(User).limit(5)):
            print("   ", u)
