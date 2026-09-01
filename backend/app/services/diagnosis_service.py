from typing import Optional, Tuple

from app.models.transaction import Transaction
from app.schemas.diagnosis import DiagnosisCategory, RecommendedNextStep, DiagnosisResult

ERROR_REASON_MAP: dict[str, DiagnosisCategory] = {
    "insufficient_funds": DiagnosisCategory.insufficient_funds,
    "issuer_timeout": DiagnosisCategory.bank_timeout,
    "issuer_down": DiagnosisCategory.bank_unavailable,
    "issuer_unavailable": DiagnosisCategory.bank_unavailable,
    "otp_invalid": DiagnosisCategory.incorrect_otp,
    "otp_timeout": DiagnosisCategory.incorrect_otp,
    "payment_declined": DiagnosisCategory.card_declined,
    "card_declined": DiagnosisCategory.card_declined,
    "limit_exceeded": DiagnosisCategory.payment_limit_exceeded,
    "authentication_failed": DiagnosisCategory.authentication_failure,
    "fraudulent": DiagnosisCategory.fraud_or_risk_flag,
    "risk_check_failed": DiagnosisCategory.fraud_or_risk_flag,
    "gateway_error": DiagnosisCategory.technical_error,
    "server_error": DiagnosisCategory.technical_error,
}

DESCRIPTION_KEYWORD_RULES: list[tuple[list[str], DiagnosisCategory, float, str]] = [
    (["fraud", "suspicious activity", "risk check"],
     DiagnosisCategory.fraud_or_risk_flag, 0.9,
     "Description indicates a fraud/risk flag was raised"),
    (["insufficient fund", "insufficient balance", "not enough balance"],
     DiagnosisCategory.insufficient_funds, 0.9,
     "Description indicates insufficient funds in the customer's account"),
    (["cancelled by user", "checkout closed", "user closed", "customer cancelled"],
     DiagnosisCategory.customer_abandoned, 0.85,
     "Description indicates the customer abandoned checkout before completing payment"),
    (["otp", "one time password"],
     DiagnosisCategory.incorrect_otp, 0.85,
     "Description references an OTP/authentication entry failure"),
    (["issuer timeout", "no response from bank", "timed out"],
     DiagnosisCategory.bank_timeout, 0.85,
     "Description indicates the issuing bank did not respond in time"),
    (["bank server", "bank unavailable", "issuer down", "gateway down"],
     DiagnosisCategory.bank_unavailable, 0.85,
     "Description indicates the bank or gateway was unavailable"),
    (["declined by issuing bank", "card declined", "do not honour", "do not honor"],
     DiagnosisCategory.card_declined, 0.85,
     "Description indicates the card was declined by the issuing bank"),
    (["limit exceeded", "transaction limit", "daily limit"],
     DiagnosisCategory.payment_limit_exceeded, 0.85,
     "Description indicates a transaction or daily limit was exceeded"),
    (["authentication failed", "3d secure", "3ds"],
     DiagnosisCategory.authentication_failure, 0.8,
     "Description indicates a 3D Secure / authentication step failed"),
    (["server error", "internal error", "gateway error"],
     DiagnosisCategory.technical_error, 0.75,
     "Description indicates a technical or gateway-side error"),
]

CONTEXT_SOURCE_MAP: dict[str, tuple[DiagnosisCategory, float, str]] = {
    "bank": (DiagnosisCategory.bank_unavailable, 0.5,
             "No specific error detail available; Razorpay attributed the failure to the bank"),
    "customer": (DiagnosisCategory.card_declined, 0.5,
                 "No specific error detail available; Razorpay attributed the failure to the customer/payment method"),
    "gateway": (DiagnosisCategory.technical_error, 0.5,
                "No specific error detail available; Razorpay attributed the failure to the gateway"),
}

NEXT_STEP_MAP: dict[DiagnosisCategory, RecommendedNextStep] = {
    DiagnosisCategory.insufficient_funds: RecommendedNextStep.notify_customer_update_payment_method,
    DiagnosisCategory.bank_timeout: RecommendedNextStep.retry_later,
    DiagnosisCategory.bank_unavailable: RecommendedNextStep.retry_later,
    DiagnosisCategory.incorrect_otp: RecommendedNextStep.request_customer_reauth,
    DiagnosisCategory.card_declined: RecommendedNextStep.notify_customer_update_payment_method,
    DiagnosisCategory.payment_limit_exceeded: RecommendedNextStep.notify_customer_update_payment_method,
    DiagnosisCategory.authentication_failure: RecommendedNextStep.request_customer_reauth,
    DiagnosisCategory.technical_error: RecommendedNextStep.retry_later,
    DiagnosisCategory.fraud_or_risk_flag: RecommendedNextStep.do_not_retry_escalate,
    DiagnosisCategory.customer_abandoned: RecommendedNextStep.notify_customer_reminder,
    DiagnosisCategory.unknown: RecommendedNextStep.manual_review,
}


def _extract_error_details(transaction: Transaction) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    payload = transaction.raw_webhook_payload or {}
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    error_reason = payment_entity.get("error_reason")
    error_description = payment_entity.get("error_description") or transaction.failure_reason
    error_source = payment_entity.get("error_source")

    return error_reason, error_description, error_source


def _diagnose_from_error_reason(error_reason: Optional[str]) -> Optional[DiagnosisResult]:
    if not error_reason:
        return None
    category = ERROR_REASON_MAP.get(error_reason.lower())
    if category is None:
        return None
    return DiagnosisResult(
        category=category,
        confidence=0.95,
        reason=f"Matched explicit Razorpay error_reason '{error_reason}'",
        recommended_next_step=NEXT_STEP_MAP[category],
    )


def _diagnose_from_description(description: Optional[str]) -> Optional[DiagnosisResult]:
    if not description:
        return None
    text = description.lower()
    for keywords, category, confidence, reason in DESCRIPTION_KEYWORD_RULES:
        if any(keyword in text for keyword in keywords):
            return DiagnosisResult(
                category=category,
                confidence=confidence,
                reason=reason,
                recommended_next_step=NEXT_STEP_MAP[category],
            )
    return None


def _diagnose_from_context(error_source: Optional[str]) -> Optional[DiagnosisResult]:
    if not error_source:
        return None
    mapped = CONTEXT_SOURCE_MAP.get(error_source.lower())
    if mapped is None:
        return None
    category, confidence, reason = mapped
    return DiagnosisResult(
        category=category,
        confidence=confidence,
        reason=reason,
        recommended_next_step=NEXT_STEP_MAP[category],
    )


def _unknown_result() -> DiagnosisResult:
    return DiagnosisResult(
        category=DiagnosisCategory.unknown,
        confidence=0.3,
        reason="No error code, description, or contextual signal was sufficient to classify this failure",
        recommended_next_step=NEXT_STEP_MAP[DiagnosisCategory.unknown],
    )


def diagnose_transaction(transaction: Transaction) -> DiagnosisResult:
    """
    Pure, read-only diagnosis. Layered lookup: error_reason -> description
    keywords -> error_source context -> unknown. Never modifies state.
    """
    error_reason, error_description, error_source = _extract_error_details(transaction)

    result = _diagnose_from_error_reason(error_reason)
    if result:
        return result

    result = _diagnose_from_description(error_description)
    if result:
        return result

    result = _diagnose_from_context(error_source)
    if result:
        return result

    return _unknown_result()
