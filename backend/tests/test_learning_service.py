from datetime import datetime

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.models import Merchant, Transaction, TransactionStatus, RecoveryAttempt, RecoveryStatus
from app.schemas.diagnosis import DiagnosisCategory, DiagnosisResult, RecommendedNextStep
from app.schemas.recovery import RecoveryStrategy, DecisionContext
from app.services.learning_service import get_strategy_performance_signal, get_all_strategy_signals
from app.services.recovery_strategy_service import decide_recovery_strategy


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _merchant(session) -> Merchant:
    m = Merchant(name="Test", razorpay_key_id="rzp_test_learning")
    session.add(m)
    session.flush()
    return m


def _card_declined_txn(session, merchant, status, order_id) -> Transaction:
    txn = Transaction(
        merchant_id=merchant.id, razorpay_order_id=order_id, amount=50000, currency="INR", status=status,
        failure_reason="Payment declined by issuing bank - do not honour",
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session.add(txn)
    session.flush()
    return txn


def _attempt(session, txn, strategy):
    session.add(RecoveryAttempt(transaction_id=txn.id, strategy=strategy.value, status=RecoveryStatus.pending, created_at=datetime.utcnow()))


def test_insufficient_history_falls_back_to_none(session):
    merchant = _merchant(session)
    txn = _card_declined_txn(session, merchant, TransactionStatus.recovered, "order_1")
    _attempt(session, txn, RecoveryStrategy.payment_link)
    session.commit()
    signal = get_strategy_performance_signal(session, RecoveryStrategy.payment_link, DiagnosisCategory.card_declined)
    assert signal is None


def test_sufficient_history_produces_signal(session):
    merchant = _merchant(session)
    for i in range(4):
        txn = _card_declined_txn(session, merchant, TransactionStatus.recovered, f"order_recovered_{i}")
        _attempt(session, txn, RecoveryStrategy.payment_link)
    failed_txn = _card_declined_txn(session, merchant, TransactionStatus.failed, "order_failed_1")
    _attempt(session, failed_txn, RecoveryStrategy.payment_link)
    session.commit()
    signal = get_strategy_performance_signal(session, RecoveryStrategy.payment_link, DiagnosisCategory.card_declined)
    assert signal == 0.8


def test_historical_signal_changes_final_scoring(session):
    merchant = _merchant(session)
    for i in range(5):
        txn = _card_declined_txn(session, merchant, TransactionStatus.recovered, f"order_hist_{i}")
        _attempt(session, txn, RecoveryStrategy.payment_link)
    session.commit()

    signals = get_all_strategy_signals(session, DiagnosisCategory.card_declined)
    assert signals.get(RecoveryStrategy.payment_link) == 1.0

    diagnosis = DiagnosisResult(category=DiagnosisCategory.card_declined, confidence=0.9, reason="test",
                                 recommended_next_step=RecommendedNextStep.notify_customer_update_payment_method)
    context = DecisionContext(amount=50000, currency="INR", diagnosis_category=DiagnosisCategory.card_declined, previous_recovery_attempts=0)

    without_history = decide_recovery_strategy(diagnosis, context)
    with_history = decide_recovery_strategy(diagnosis, context, signals)

    score_without = next(c.score for c in without_history.candidate_strategies if c.strategy == RecoveryStrategy.payment_link)
    score_with = next(c.score for c in with_history.candidate_strategies if c.strategy == RecoveryStrategy.payment_link)
    assert score_with > score_without
