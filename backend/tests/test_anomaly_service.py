from datetime import datetime, timedelta

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.models import Merchant, Transaction, TransactionStatus
from app.services.anomaly_service import detect_anomalies


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _merchant(session) -> Merchant:
    m = Merchant(name="Test", razorpay_key_id="rzp_test_anomaly")
    session.add(m)
    session.flush()
    return m


def _failed_txn(session, merchant, hours_ago, order_suffix, failure_reason="generic failure"):
    txn = Transaction(
        merchant_id=merchant.id, razorpay_order_id=f"order_{order_suffix}", amount=50000, currency="INR",
        status=TransactionStatus.failed, failure_reason=failure_reason,
        created_at=datetime.utcnow() - timedelta(hours=hours_ago), updated_at=datetime.utcnow(),
    )
    session.add(txn)
    session.flush()
    return txn


def test_no_anomaly_with_low_stable_volume(session):
    merchant = _merchant(session)
    for i, h in enumerate([1, 5, 10, 30, 40]):
        _failed_txn(session, merchant, h, f"n{i}")
    session.commit()
    report = detect_anomalies(session)
    assert report.anomalies == []


def test_failure_spike_detected(session):
    merchant = _merchant(session)
    for i, h in enumerate([30, 35, 40]):
        _failed_txn(session, merchant, h, f"baseline{i}")
    for i in range(20):
        _failed_txn(session, merchant, i % 20, f"recent{i}")
    session.commit()
    report = detect_anomalies(session)
    assert "failure_spike" in [a.pattern for a in report.anomalies]


def test_bank_specific_spike_detected(session):
    merchant = _merchant(session)
    for i in range(8):
        _failed_txn(session, merchant, i, f"bank{i}", failure_reason="Issuer timeout, no response from bank")
    session.commit()
    report = detect_anomalies(session)
    assert "bank_timeout_spike" in [a.pattern for a in report.anomalies]
