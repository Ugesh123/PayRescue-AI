from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.models import Merchant, Transaction, TransactionStatus


@pytest.fixture
def client_with_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client, engine
    app.dependency_overrides.clear()


def test_recover_nonexistent_transaction_returns_404(client_with_db):
    client, _ = client_with_db
    response = client.post("/transactions/9999/recover")
    assert response.status_code == 404


def test_recover_non_failed_transaction_returns_422(client_with_db):
    client, engine = client_with_db
    with Session(engine) as session:
        merchant = Merchant(name="Test Merchant", razorpay_key_id="rzp_test_api")
        session.add(merchant)
        session.flush()
        txn = Transaction(
            merchant_id=merchant.id, razorpay_order_id="order_api_1", amount=50000, currency="INR",
            status=TransactionStatus.captured, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        session.add(txn)
        session.commit()
        txn_id = txn.id

    response = client.post(f"/transactions/{txn_id}/recover")
    assert response.status_code == 422


def test_recovery_attempts_endpoint_returns_empty_list_for_new_transaction(client_with_db):
    client, engine = client_with_db
    with Session(engine) as session:
        merchant = Merchant(name="Test Merchant", razorpay_key_id="rzp_test_api2")
        session.add(merchant)
        session.flush()
        txn = Transaction(
            merchant_id=merchant.id, razorpay_order_id="order_api_2", amount=50000, currency="INR",
            status=TransactionStatus.failed, failure_reason="Issuer timeout, no response from bank",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        session.add(txn)
        session.commit()
        txn_id = txn.id

    response = client.get(f"/transactions/{txn_id}/recovery-attempts")
    assert response.status_code == 200
    assert response.json() == []
