from datetime import datetime
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool

from app.models import Merchant, Transaction, TransactionStatus, RecoveryAttempt
from app.schemas.recovery import RecoveryStrategy, Urgency, RecoveryDecision
from app.schemas.execution import ExecutionStatus
from app.services.recovery_execution_service import execute_recovery
from app.services.razorpay_client import RazorpayClientError


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_transaction(session, amount: int = 89900) -> Transaction:
    merchant = Merchant(name="Test Merchant", razorpay_key_id="rzp_test_x")
    session.add(merchant)
    session.flush()
    txn = Transaction(
        merchant_id=merchant.id, razorpay_order_id="order_test_1", razorpay_payment_id="pay_test_1",
        amount=amount, currency="INR", status=TransactionStatus.failed, failure_reason="test failure",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def _make_decision(strategy, requires_human_review=False, requires_customer_action=False) -> RecoveryDecision:
    return RecoveryDecision(
        strategy=strategy, confidence=0.8, reason="test reason", urgency=Urgency.low,
        estimated_success_probability=0.6, requires_customer_action=requires_customer_action,
        requires_human_review=requires_human_review, next_step="test next step", candidate_strategies=[],
    )


def test_payment_link_execution_success(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.payment_link, requires_customer_action=True)
    with patch("app.services.recovery_execution_service.create_payment_link", return_value="https://rzp.io/l/testlink123"):
        result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.success
    assert result.payment_link_url == "https://rzp.io/l/testlink123"
    stored = session.get(RecoveryAttempt, result.recovery_attempt_id)
    assert stored.transaction_id == txn.id
    assert stored.strategy == RecoveryStrategy.payment_link.value


def test_payment_link_execution_failure_is_recorded(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.payment_link, requires_customer_action=True)
    with patch("app.services.recovery_execution_service.create_payment_link", side_effect=RazorpayClientError("simulated failure")):
        result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.failed
    assert result.payment_link_url is None


def test_escalate_execution(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.escalate, requires_human_review=True)
    result = execute_recovery(session, txn, decision)
    assert result.strategy == RecoveryStrategy.escalate
    assert result.evidence is not None
    assert result.evidence["transaction_id"] == txn.id


def test_reminder_execution_is_simulated(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.reminder, requires_customer_action=True)
    result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.simulated


def test_customer_update_payment_method_execution_is_simulated(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.customer_update_payment_method, requires_customer_action=True)
    result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.simulated


def test_customer_reauthentication_execution_is_simulated(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.customer_reauthentication, requires_customer_action=True)
    result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.simulated


def test_alternate_payment_method_execution_is_simulated(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.alternate_payment_method)
    result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.simulated
    assert result.payment_link_url is None


def test_retry_later_does_not_charge_and_is_scheduled(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.retry_later)
    result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.scheduled


def test_retry_same_route_does_not_charge_and_is_scheduled(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.retry_same_route)
    result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.scheduled


def test_no_action_execution(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.no_action)
    result = execute_recovery(session, txn, decision)
    assert result.execution_status == ExecutionStatus.success
    assert result.strategy == RecoveryStrategy.no_action


def test_requires_human_review_forces_escalate_even_if_strategy_was_automatic(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.retry_later, requires_human_review=True)
    result = execute_recovery(session, txn, decision)
    assert result.strategy == RecoveryStrategy.escalate
    assert result.requires_human_review is True


def test_recovery_attempt_is_recorded_for_every_execution(session):
    txn = _make_transaction(session)
    decision = _make_decision(RecoveryStrategy.reminder, requires_customer_action=True)
    result = execute_recovery(session, txn, decision)
    attempts = session.exec(select(RecoveryAttempt).where(RecoveryAttempt.transaction_id == txn.id)).all()
    assert len(attempts) == 1
    assert attempts[0].id == result.recovery_attempt_id
