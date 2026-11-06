"""钱包接口：转账（事务实战）。"""

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import User
from app.services import user_service

router = APIRouter(tags=["wallet"])


class TransferIn(BaseModel):
    to_user_id: int = Field(description="收款方用户 id")
    amount: Decimal = Field(gt=0, description="转账金额,必须大于 0")


class TransferOut(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: Decimal
    from_balance: Decimal
    to_balance: Decimal


@router.post("/transfer", response_model=TransferOut, summary="转账(需登录)")
def transfer(
    payload: TransferIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransferOut:
    src, dst = user_service.transfer(db, current_user.id, payload.to_user_id, payload.amount)
    return TransferOut(
        from_user_id=src.id,
        to_user_id=dst.id,
        amount=payload.amount,
        from_balance=src.balance,
        to_balance=dst.balance,
    )
