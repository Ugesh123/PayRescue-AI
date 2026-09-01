from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, JSON


class TransactionStatus(str, Enum):
    created = "created"
    failed = "failed"
    captured = "captured"
    recovered = "recovered"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)

    merchant_id: int = Field(foreign_key="merchants.id", nullable=False, index=True)

    razorpay_order_id: str = Field(nullable=False, max_length=255, index=True)
    razorpay_payment_id: Optional[str] = Field(default=None, max_length=255, index=True)

    amount: int = Field(nullable=False)  # stored in paise, matches Razorpay convention
    currency: str = Field(default="INR", nullable=False, max_length=10)

    # Explicit String column (not a native Postgres ENUM) so this matches
    # the hand-authored migration exactly and autogenerate never proposes
    # an unexpected type change.
    status: TransactionStatus = Field(
        default=TransactionStatus.created,
        sa_column=Column(String(20), nullable=False, index=True),
    )
    failure_reason: Optional[str] = Field(default=None, max_length=500)

    raw_webhook_payload: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    merchant: Optional["Merchant"] = Relationship(back_populates="transactions")
    recovery_attempts: List["RecoveryAttempt"] = Relationship(back_populates="transaction")
