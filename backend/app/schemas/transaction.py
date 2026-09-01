from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.transaction import TransactionStatus


class TransactionRead(BaseModel):
    id: int
    merchant_id: int
    razorpay_order_id: str
    razorpay_payment_id: Optional[str]
    amount: int
    currency: str
    status: TransactionStatus
    failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[TransactionRead]
