from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.models.recovery_attempt import RecoveryStatus
from app.schemas.recovery import RecoveryStrategy


class ExecutionStatus(str, Enum):
    success = "success"
    simulated = "simulated"
    scheduled = "scheduled"
    blocked = "blocked"
    failed = "failed"


class ExecutionResult(BaseModel):
    strategy: RecoveryStrategy
    execution_status: ExecutionStatus
    action_taken: str
    message: str
    recovery_attempt_id: Optional[int] = None
    payment_link_url: Optional[str] = None
    requires_customer_action: bool
    requires_human_review: bool
    evidence: Optional[dict] = None


class RecoveryAttemptRead(BaseModel):
    id: int
    transaction_id: int
    strategy: Optional[str]
    status: RecoveryStatus
    created_at: datetime

    class Config:
        from_attributes = True
