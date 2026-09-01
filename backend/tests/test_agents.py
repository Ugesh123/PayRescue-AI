from datetime import datetime

import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool

from app.models import Merchant, Transaction, TransactionStatus, RecoveryAttempt
from app.agents.diagnosis_agent import make_diagnosis_node
from app.agents.strategy_agent import make_strategy_node
from app.agents.execution_agent import make_safety_node, make_execution_node
from app.agents.graph import build_recovery_graph
from app.schemas.diagnosis import DiagnosisCategory
from app.schemas.recovery import RecoveryStrategy, Urgency, RecoveryDecision


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_failed_transaction(session, failure_reason="Issuer timeout, no response from bank") -> Transaction:
    merchant = Merchant(name="Test Merchant", razorpay_key_id="rzp_test_agents")
    session.add(merchant)
    session.flush()
    txn = Transaction(
        merchant_id=merchant.id, razorpay_order_id="order_agent_1", razorpay_payment_id="pay_agent_1",
        amount=89900, currency="INR", status=TransactionStatus.failed, failure_reason=failure_reason,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def test_diagnosis_node_produces_diagnosis(session):
    txn = _make_failed_transaction(session)
    node = make_diagnosis_node()
    result = node({"transaction_id": txn.id, "transaction": txn})
    assert result["diagnosis"].category == DiagnosisCategory.bank_timeout


def test_strategy_node_produces_decision(session):
    txn = _make_failed_transaction(session)
    diagnosis_output = make_diagnosis_node()({"transaction_id": txn.id, "transaction": txn})
    state = {"transaction_id": txn.id, "transaction": txn, **diagnosis_output}
    result = make_strategy_node(session)(state)
    assert result["decision"].strategy == RecoveryStrategy.retry_later


def test_safety_node_blocks_when_human_review_required():
    decision = RecoveryDecision(strategy=RecoveryStrategy.retry_later, confidence=0.5, reason="test", urgency=Urgency.high,
                                 estimated_success_probability=0.3, requires_customer_action=False,
                                 requires_human_review=True, next_step="test", candidate_strategies=[])
    result = make_safety_node()({"decision": decision})
    assert result["safety_blocked"] is True


def test_safety_node_passes_when_no_review_required():
    decision = RecoveryDecision(strategy=RecoveryStrategy.retry_later, confidence=0.8, reason="test", urgency=Urgency.low,
                                 estimated_success_probability=0.6, requires_customer_action=False,
                                 requires_human_review=False, next_step="test", candidate_strategies=[])
    result = make_safety_node()({"decision": decision})
    assert result["safety_blocked"] is False


def test_execution_node_invokes_execution_service(session):
    txn = _make_failed_transaction(session)
    decision = RecoveryDecision(strategy=RecoveryStrategy.no_action, confidence=0.5, reason="test", urgency=Urgency.low,
                                 estimated_success_probability=0.5, requires_customer_action=False,
                                 requires_human_review=False, next_step="test", candidate_strategies=[])
    result = make_execution_node(session)({"transaction": txn, "decision": decision})
    assert result["execution_result"].strategy == RecoveryStrategy.no_action
    attempts = session.exec(select(RecoveryAttempt).where(RecoveryAttempt.transaction_id == txn.id)).all()
    assert len(attempts) == 1


def test_full_graph_reaches_end_with_execution_result(session):
    txn = _make_failed_transaction(session, failure_reason="Suspicious activity flagged by risk engine")
    graph = build_recovery_graph(session)
    final_state = graph.invoke({"transaction_id": txn.id})
    assert final_state["execution_result"] is not None
    assert final_state["execution_result"].strategy == RecoveryStrategy.escalate
    assert final_state["decision"].requires_human_review is True
