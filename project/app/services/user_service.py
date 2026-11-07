"""用户业务逻辑：所有对 users 表的读写都收在这里。

为什么要有这一层：
    路由层只负责 HTTP（收参数、返响应）,不碰 Session、不写 SQL；
    事务边界放在这里——一个函数就是一个工作单元,成功 commit,失败 rollback。

调用方只需要知道"做什么",不需要知道"怎么查、怎么提交"。
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models import Role, User


def create_user(
    db: Session,
    username: str,
    phone: str,
    balance: Decimal = Decimal("0.00"),
) -> User:
    """新增用户。用户名或手机号重复时抛 ConflictError（409）。"""
    user = User(username=username, phone=phone, balance=balance)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:          # ⚠️ 唯一键冲突在这里才会暴露
        db.rollback()
        raise ConflictError(f"用户名或手机号已存在：{username}") from exc
    db.refresh(user)                       # 拿回数据库生成的值（id / created_at）
    return user


def get_user(db: Session, user_id: int) -> User:
    """按主键查。查不到抛 NotFoundError（404）。"""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"用户 {user_id} 不存在")
    return user


def list_users(db: Session, page: int = 1, size: int = 10) -> tuple[list[User], int]:
    """分页查询,返回 (当页数据, 总数)。默认只返回未删除的用户。"""
    total = db.scalar(
        select(func.count()).select_from(User).where(User.is_deleted == 0)
    ) or 0
    stmt = (
        select(User)
        .where(User.is_deleted == 0)      # 💡 软删的过滤集中在这里,路由层不用管
        .order_by(User.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(stmt)), total


def update_balance(db: Session, user_id: int, amount: Decimal) -> User:
    """把余额调整 amount（可正可负）,返回更新后的用户。"""
    user = get_user(db, user_id)
    user.balance = user.balance + amount       # 💡 改属性即可,脏检查负责生成 UPDATE
    db.commit()
    db.refresh(user)
    return user


def soft_delete(db: Session, user_id: int) -> User:
    """软删除：只把 is_deleted 置 1,行还在,可以恢复。"""
    user = get_user(db, user_id)
    user.is_deleted = 1
    db.commit()
    db.refresh(user)
    return user


def hard_delete(db: Session, user_id: int) -> None:
    """硬删除：真删。⚠️ 不可恢复,只用于确实不要的数据。"""
    user = get_user(db, user_id)
    db.delete(user)
    db.commit()


# ---- 角色相关（第七章）--------------------------------------------


def assign_role(db: Session, user_id: int, role_name: str) -> list[str]:
    """给用户分配角色。角色不存在时抛 NotFoundError。"""
    user = get_user(db, user_id)
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise NotFoundError(f"角色 {role_name} 不存在")

    if role not in user.roles:          # 中间表是联合主键,重复添加也安全,但没必要发 SQL
        user.roles.append(role)
        db.commit()
    return [r.name for r in user.roles]


def list_roles(db: Session, user_id: int) -> list[str]:
    """查询用户已有的角色名。"""
    user = get_user(db, user_id)
    return [r.name for r in user.roles]


# ---- 转账（第七章：事务实战）--------------------------------------


def transfer(db: Session, from_id: int, to_id: int, amount: Decimal) -> tuple[User, User]:
    """两个用户之间转账。任一步失败则整体回滚。

    ⚠️ 这里用"读出来改属性"的写法,并发下存在丢更新风险,见第五章 5.6。
       生产环境应改用 with_for_update() 或原子 SQL。
    """
    if amount <= 0:
        raise AppError("转账金额必须大于 0")
    if from_id == to_id:
        raise AppError("不能给自己转账")

    src = get_user(db, from_id)
    dst = get_user(db, to_id)
    if src.balance < amount:
        raise AppError(f"余额不足,当前余额 {src.balance}")

    try:
        src.balance = src.balance - amount
        dst.balance = dst.balance + amount
        db.commit()                      # 两条 UPDATE 在同一个事务里
    except Exception:
        db.rollback()                    # 任何一步出错,两边都撤销
        raise

    db.refresh(src)
    db.refresh(dst)
    return src, dst
