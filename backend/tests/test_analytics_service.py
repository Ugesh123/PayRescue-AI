from datetime import datetime

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.models import Merchant, Transaction, TransactionStatus, RecoveryAttempt, RecoveryStatus
from app.services.analytics_service import compute_recovery_analytics


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _merchant(session) -> Merchant:
    m = Merchant(name="Test", razorpay_key_id="rzp_test_analytics")
    session.add(m)
    session.flush()
    return m


def _txn(session, merchant, status, amount, order_id, failure_reason=None):
    txn = Transaction(
        merchant_id=merchant.id, razorpay_order_id=order_id, amount=amount, currency="INR",
        status=status, failure_reason=failure_reason, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session.add(txn)
    session.flush()
    return txn


def test_recovery_rate_and_revenue(session):
    merchant = _merchant(session)
    _txn(session, merchant, TransactionStatus.failed, 50000, "order_1", "insufficient funds")
    _txn(session, merchant, TransactionStatus.recovered, 100000, "order_2", "card declined")
    session.commit()
    analytics = compute_recovery_analytics(session)
    assert analytics.total_failed == 1
    assert analytics.total_recovered == 1
    assert analytics.recovery_rate == 0.5
    assert analytics.revenue_at_risk == 50000
    assert analytics.revenue_recovered == 100000


def test_strategy_success_rate(session):
    merchant = _merchant(session)
    recovered_txn = _txn(session, merchant, TransactionStatus.recovered, 100000, "order_3")
    failed_txn = _txn(session, merchant, TransactionStatus.failed, 50000, "order_4")
    session.add(RecoveryAttempt(transaction_id=recovered_txn.id, strategy="payment_link", status=RecoveryStatus.success, created_at=datetime.utcnow()))
    session.add(RecoveryAttempt(transaction_id=failed_txn.id, strategy="payment_link", status=RecoveryStatus.pending, created_at=datetime.utcnow()))
    session.commit()
    analytics = compute_recovery_analytics(session)
    strategy_perf = {s.strategy: s for s in analytics.strategy_performance}
    assert strategy_perf["payment_link"].total_attempts == 2
    assert strategy_perf["payment_link"].successful_attempts == 1
    assert analytics.most_successful_strategy == "payment_link"


def test_category_success_rate(session):
    merchant = _merchant(session)
    _txn(session, merchant, TransactionStatus.recovered, 100000, "order_5", "Issuer timeout, no response from bank")
    _txn(session, merchant, TransactionStatus.failed, 50000, "order_6", "Issuer timeout, no response from bank")
    session.commit()
    analytics = compute_recovery_analytics(session)
    category_perf = {c.category: c for c in analytics.category_performance}
    assert category_perf["bank_timeout"].total_failed == 2
    assert category_perf["bank_timeout"].total_recovered == 1
    assert category_perf["bank_timeout"].recovery_rate == 0.5
