from enum import Enum

from pydantic import BaseModel, Field


class DiagnosisCategory(str, Enum):
    insufficient_funds = "insufficient_funds"
    bank_timeout = "bank_timeout"
    bank_unavailable = "bank_unavailable"
    incorrect_otp = "incorrect_otp"
    card_declined = "card_declined"
    payment_limit_exceeded = "payment_limit_exceeded"
    authentication_failure = "authentication_failure"
    technical_error = "technical_error"
    fraud_or_risk_flag = "fraud_or_risk_flag"
    customer_abandoned = "customer_abandoned"
    unknown = "unknown"


class RecommendedNextStep(str, Enum):
    retry_later = "retry_later"
    retry_alternate_route = "retry_alternate_route"
    request_customer_reauth = "request_customer_reauth"
    notify_customer_update_payment_method = "notify_customer_update_payment_method"
    notify_customer_reminder = "notify_customer_reminder"
    do_not_retry_escalate = "do_not_retry_escalate"
    manual_review = "manual_review"


class DiagnosisResult(BaseModel):
    category: DiagnosisCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    recommended_next_step: RecommendedNextStep
