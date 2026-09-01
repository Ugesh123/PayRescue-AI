from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String


class RecoveryStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class RecoveryAttempt(SQLModel, table=True):
    __tablename__ = "recovery_attempts"

    id: Optional[int] = Field(default=None, primary_key=True)

    transaction_id: int = Field(foreign_key="transactions.id", nullable=False, index=True)

    # Free-text (not an Enum) on purpose - future strategy names don't
    # require a migration to add.
    strategy: Optional[str] = Field(default=None, max_length=100)

    status: RecoveryStatus = Field(
        default=RecoveryStatus.pending,
        sa_column=Column(String(20), nullable=False, index=True),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    transaction: Optional["Transaction"] = Relationship(back_populates="recovery_attempts")
