from datetime import datetime
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool

from app.models import Merchant, Transaction, TransactionStatus, RecoveryAttempt, RecoveryStatus
from app.schemas.recovery import RecoveryStrategy, Urgency, RecoveryDecision
from app.services.recovery_execution_service import execute_recovery
from app.services.webhook_service import process_webhook_event
from app.services.analytics_service import compute_recovery_analytics


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_failed_transaction(session, order_id="order_closed_loop_1") -> Transaction:
    merchant = Merchant(name="Test Merchant", razorpay_key_id="rzp_test_closed_loop")
    session.add(merchant)
    session.flush()
    txn = Transaction(
        merchant_id=merchant.id, razorpay_order_id=order_id, razorpay_payment_id="pay_original_failed",
        amount=89900, currency="INR", status=TransactionStatus.failed,
        failure_reason="Payment declined by issuing bank - do not honour",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def _payment_link_decision() -> RecoveryDecision:
    return RecoveryDecision(strategy=RecoveryStrategy.payment_link, confidence=0.7, reason="test", urgency=Urgency.low,
                             estimated_success_probability=0.5, requires_customer_action=True,
                             requires_human_review=False, next_step="test", candidate_strategies=[])


def _payment_link_paid_payload(transaction_id: int, payment_id: str, order_id: str) -> dict:
    return {
        "entity": "event",
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {"id": "plink_TEST001", "reference_id": f"payrescue_{transaction_id}", "status": "paid"}},
            "payment": {"entity": {"id": payment_id, "order_id": order_id, "amount": 89900, "currency": "INR",
                                    "status": "captured", "notes": {"payrescue_transaction_id": str(transaction_id)}}},
        },
    }


def _payment_captured_payload(payment_id: str, order_id: str, notes=None) -> dict:
    entity = {"id": payment_id, "order_id": order_id, "amount": 50000, "currency": "INR", "status": "captured"}
    if notes:
        entity["notes"] = notes
    return {"entity": "event", "event": "payment.captured", "payload": {"payment": {"entity": entity}}}


def test_failed_transaction_generates_payment_link_with_linking_notes(session):
    txn = _make_failed_transaction(session)
    with patch("app.services.recovery_execution_service.create_payment_link", return_value="https://rzp.io/l/closedloop123") as mock_create:
        result = execute_recovery(session, txn, _payment_link_decision())
    assert result.payment_link_url == "https://rzp.io/l/closedloop123"
    _, kwargs = mock_create.call_args
    assert kwargs["reference_id"] == f"payrescue_{txn.id}"
    assert kwargs["notes"] == {"payrescue_transaction_id": str(txn.id)}


def test_successful_payment_link_payment_recovers_original_transaction(session):
    txn = _make_failed_transaction(session)
    with patch("app.services.recovery_execution_service.create_payment_link", return_value="https://rzp.io/l/closedloop123"):
        execute_recovery(session, txn, _payment_link_decision())

    payload = _payment_link_paid_payload(txn.id, "pay_new_success_1", "order_new_link_1")
    result = process_webhook_event(session, payload)

    assert result["status"] == "processed"
    assert result["transaction_status"] == "recovered"

    session.refresh(txn)
    assert txn.status == TransactionStatus.recovered
    assert txn.razorpay_payment_id == "pay_new_success_1"

    attempts = session.exec(select(RecoveryAttempt).where(RecoveryAttempt.transaction_id == txn.id)).all()
    assert len(attempts) == 1
    assert attempts[0].status == RecoveryStatus.success

    all_transactions = session.exec(select(Transaction)).all()
    assert len(all_transactions) == 1


def test_repeated_success_webhook_does_not_duplicate_anything(session):
    txn = _make_failed_transaction(session)
    with patch("app.services.recovery_execution_service.create_payment_link", return_value="https://rzp.io/l/closedloop123"):
        execute_recovery(session, txn, _payment_link_decision())

    payload = _payment_link_paid_payload(txn.id, "pay_new_success_1", "order_new_link_1")
    process_webhook_event(session, payload)
    result_second = process_webhook_event(session, payload)

    assert result_second["transaction_status"] == "recovered"
    all_transactions = session.exec(select(Transaction)).all()
    assert len(all_transactions) == 1
    attempts = session.exec(select(RecoveryAttempt).where(RecoveryAttempt.transaction_id == txn.id)).all()
    assert len(attempts) == 1
    assert attempts[0].status == RecoveryStatus.success


def test_unrelated_successful_payment_creates_normal_transaction(session):
    _make_failed_transaction(session)
    payload = _payment_captured_payload("pay_unrelated_1", "order_unrelated_1")
    result = process_webhook_event(session, payload)
    assert result["status"] == "processed"
    assert result["transaction_status"] == "captured"
    all_transactions = session.exec(select(Transaction)).all()
    assert len(all_transactions) == 2


def test_unresolvable_reference_is_a_safe_fallback(session):
    _make_failed_transaction(session)
    payload = _payment_link_paid_payload(transaction_id=999999, payment_id="pay_x", order_id="order_x")
    result = process_webhook_event(session, payload)
    assert result["status"] == "ignored"
    assert result["reason"] == "unresolvable reference"
    all_transactions = session.exec(select(Transaction)).all()
    assert len(all_transactions) == 1
    assert all_transactions[0].status == TransactionStatus.failed


def test_analytics_reflects_the_real_recovered_transaction(session):
    txn = _make_failed_transaction(session)
    with patch("app.services.recovery_execution_service.create_payment_link", return_value="https://rzp.io/l/closedloop123"):
        execute_recovery(session, txn, _payment_link_decision())
    payload = _payment_link_paid_payload(txn.id, "pay_new_success_1", "order_new_link_1")
    process_webhook_event(session, payload)

    analytics = compute_recovery_analytics(session)
    assert analytics.total_recovered == 1
    assert analytics.total_failed == 0
    assert analytics.revenue_recovered == 89900
    strategy_perf = {s.strategy: s for s in analytics.strategy_performance}
    assert strategy_perf["payment_link"].successful_attempts == 1
    assert strategy_perf["payment_link"].success_rate == 1.0


def test_recovery_history_shows_the_successful_recovery(session):
    txn = _make_failed_transaction(session)
    with patch("app.services.recovery_execution_service.create_payment_link", return_value="https://rzp.io/l/closedloop123"):
        execute_recovery(session, txn, _payment_link_decision())
    payload = _payment_link_paid_payload(txn.id, "pay_new_success_1", "order_new_link_1")
    process_webhook_event(session, payload)

    attempts = session.exec(
        select(RecoveryAttempt).where(RecoveryAttempt.transaction_id == txn.id).order_by(RecoveryAttempt.created_at.desc())
    ).all()
    assert len(attempts) == 1
    assert attempts[0].strategy == RecoveryStrategy.payment_link.value
    assert attempts[0].status == RecoveryStatus.success
