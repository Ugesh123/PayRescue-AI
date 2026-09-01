from datetime import datetime

from app.models.transaction import Transaction, TransactionStatus
from app.schemas.diagnosis import DiagnosisCategory, RecommendedNextStep
from app.services.diagnosis_service import diagnose_transaction


def _make_transaction(failure_reason=None, raw_webhook_payload=None) -> Transaction:
    return Transaction(
        id=1, merchant_id=1, razorpay_order_id="order_test_001", razorpay_payment_id="pay_test_001",
        amount=50000, currency="INR", status=TransactionStatus.failed,
        failure_reason=failure_reason, raw_webhook_payload=raw_webhook_payload,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


def _payload_with_error(error_reason=None, error_description=None, error_source=None) -> dict:
    entity = {}
    if error_reason:
        entity["error_reason"] = error_reason
    if error_description:
        entity["error_description"] = error_description
    if error_source:
        entity["error_source"] = error_source
    return {"payload": {"payment": {"entity": entity}}}


def test_insufficient_funds_via_error_reason():
    txn = _make_transaction(raw_webhook_payload=_payload_with_error(error_reason="insufficient_funds"))
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.insufficient_funds
    assert result.confidence >= 0.9


def test_bank_timeout_via_description():
    txn = _make_transaction(raw_webhook_payload=_payload_with_error(error_description="Issuer timeout, no response from bank"))
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.bank_timeout


def test_bank_unavailable_via_description():
    txn = _make_transaction(raw_webhook_payload=_payload_with_error(error_description="Bank server is currently unavailable"))
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.bank_unavailable


def test_incorrect_otp_via_description():
    txn = _make_transaction(raw_webhook_payload=_payload_with_error(error_description="Incorrect OTP entered by customer"))
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.incorrect_otp


def test_card_declined_via_description():
    txn = _make_transaction(raw_webhook_payload=_payload_with_error(error_description="Payment declined by issuing bank - do not honour"))
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.card_declined


def test_fraud_flag_never_recommends_retry():
    txn = _make_transaction(raw_webhook_payload=_payload_with_error(error_reason="fraudulent"))
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.fraud_or_risk_flag
    assert result.recommended_next_step == RecommendedNextStep.do_not_retry_escalate


def test_context_fallback_from_error_source():
    txn = _make_transaction(raw_webhook_payload=_payload_with_error(error_source="bank"))
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.bank_unavailable
    assert result.confidence == 0.5


def test_unknown_when_no_signals_present():
    txn = _make_transaction(raw_webhook_payload=None, failure_reason=None)
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.unknown


def test_falls_back_to_failure_reason_when_payload_missing():
    txn = _make_transaction(raw_webhook_payload=None, failure_reason="Payment failed due to insufficient funds in account")
    result = diagnose_transaction(txn)
    assert result.category == DiagnosisCategory.insufficient_funds
