from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel, Field, Relationship


class Merchant(SQLModel, table=True):
    __tablename__ = "merchants"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=255)
    razorpay_key_id: str = Field(nullable=False, max_length=255, unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    transactions: List["Transaction"] = Relationship(back_populates="merchant")
