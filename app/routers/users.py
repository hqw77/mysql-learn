"""用户接口：HTTP 层，只负责收参数、返响应、定状态码。

业务全在 user_service；这里连 SQL 都不出现。
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.user import UserCreate, UserOut, UserPage, UserUpdateBalance
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserPage, summary="用户列表（分页）")
def list_users(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=100, description="每页条数，最大 100"),
    db: Session = Depends(get_db),
) -> UserPage:
    items, total = user_service.list_users(db, page=page, size=size)
    return UserPage(total=total, page=page, size=size, items=items)


@router.get("/{user_id}", response_model=UserOut, summary="用户详情")
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    return user_service.get_user(db, user_id)


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户",
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    return user_service.create_user(
        db,
        username=payload.username,
        phone=payload.phone,
        balance=payload.balance,
    )


@router.put("/{user_id}/balance", response_model=UserOut, summary="调整余额")
def update_balance(
    user_id: int,
    payload: UserUpdateBalance,
    db: Session = Depends(get_db),
) -> UserOut:
    return user_service.update_balance(db, user_id, payload.amount)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户（软删）",
)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    user_service.soft_delete(db, user_id)
