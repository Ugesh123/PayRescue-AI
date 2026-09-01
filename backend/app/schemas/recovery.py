from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from app.schemas.diagnosis import DiagnosisCategory


class RecoveryStrategy(str, Enum):
    retry_same_route = "retry_same_route"
    retry_later = "retry_later"
    alternate_payment_method = "alternate_payment_method"
    payment_link = "payment_link"
    customer_reauthentication = "customer_reauthentication"
    customer_update_payment_method = "customer_update_payment_method"
    reminder = "reminder"
    escalate = "escalate"
    no_action = "no_action"


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DecisionContext(BaseModel):
    amount: int  # paise
    currency: str
    diagnosis_category: DiagnosisCategory
    previous_recovery_attempts: int = 0


class CandidateStrategy(BaseModel):
    strategy: RecoveryStrategy
    score: float = Field(ge=0.0, le=1.0)
    estimated_success_probability: float = Field(ge=0.0, le=1.0)
    reason: str


class RecoveryDecision(BaseModel):
    strategy: RecoveryStrategy
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    urgency: Urgency
    estimated_success_probability: float = Field(ge=0.0, le=1.0)
    requires_customer_action: bool
    requires_human_review: bool
    next_step: str
    candidate_strategies: List[CandidateStrategy]
