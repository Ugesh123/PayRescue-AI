from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from app.core.database import get_session
from app.models.transaction import Transaction, TransactionStatus
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.transaction import TransactionRead, TransactionListResponse
from app.schemas.diagnosis import DiagnosisResult
from app.schemas.recovery import RecoveryDecision, DecisionContext
from app.schemas.execution import ExecutionResult, RecoveryAttemptRead
from app.services.seed_service import seed_sample_data
from app.services.diagnosis_service import diagnose_transaction
from app.services.recovery_strategy_service import decide_recovery_strategy
from app.services.recovery_execution_service import execute_recovery
from app.services.learning_service import get_all_strategy_signals
from app.agents.graph import build_recovery_graph

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[TransactionStatus] = Query(default=None),
    session: Session = Depends(get_session),
):
    base_filter = [Transaction.status == status] if status is not None else []
    count_query = select(func.count()).select_from(Transaction).where(*base_filter)
    total = session.exec(count_query).one()

    query = (
        select(Transaction)
        .where(*base_filter)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = session.exec(query).all()
    return TransactionListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    return transaction


@router.get("/{transaction_id}/diagnosis", response_model=DiagnosisResult)
def get_transaction_diagnosis(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    if transaction.status != TransactionStatus.failed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transaction {transaction_id} has status '{transaction.status.value}'; "
                "diagnosis only applies to failed transactions"
            ),
        )
    return diagnose_transaction(transaction)


def _build_decision_context(session: Session, transaction: Transaction, diagnosis: DiagnosisResult) -> DecisionContext:
    previous_attempts_count = session.exec(
        select(func.count())
        .select_from(RecoveryAttempt)
        .where(RecoveryAttempt.transaction_id == transaction.id)
    ).one()
    return DecisionContext(
        amount=transaction.amount,
        currency=transaction.currency,
        diagnosis_category=diagnosis.category,
        previous_recovery_attempts=previous_attempts_count,
    )


def _decide_recovery(session: Session, transaction: Transaction, diagnosis: DiagnosisResult) -> RecoveryDecision:
    context = _build_decision_context(session, transaction, diagnosis)
    historical_signals = get_all_strategy_signals(session, diagnosis.category)
    return decide_recovery_strategy(diagnosis, context, historical_signals)


@router.get("/{transaction_id}/recovery-strategy", response_model=RecoveryDecision)
def get_transaction_recovery_strategy(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    if transaction.status != TransactionStatus.failed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transaction {transaction_id} has status '{transaction.status.value}'; "
                "recovery strategy only applies to failed transactions"
            ),
        )

    diagnosis = diagnose_transaction(transaction)
    return _decide_recovery(session, transaction, diagnosis)


@router.post("/{transaction_id}/recover", response_model=ExecutionResult)
def recover_transaction(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    if transaction.status != TransactionStatus.failed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transaction {transaction_id} has status '{transaction.status.value}'; "
                "recovery can only be executed on failed transactions"
            ),
        )

    diagnosis = diagnose_transaction(transaction)
    decision = _decide_recovery(session, transaction, diagnosis)
    return execute_recovery(session, transaction, decision)


@router.post("/{transaction_id}/agent-recover", response_model=ExecutionResult)
def agent_recover_transaction(transaction_id: int, session: Session = Depends(get_session)):
    """Same outcome as /recover, routed through the LangGraph orchestration in app/agents/."""
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    if transaction.status != TransactionStatus.failed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Transaction {transaction_id} has status '{transaction.status.value}'; "
                "recovery can only be executed on failed transactions"
            ),
        )

    graph = build_recovery_graph(session)
    final_state = graph.invoke({"transaction_id": transaction_id})

    if final_state.get("error"):
        raise HTTPException(status_code=500, detail=final_state["error"])

    return final_state["execution_result"]


@router.get("/{transaction_id}/recovery-attempts", response_model=List[RecoveryAttemptRead])
def list_recovery_attempts(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

    attempts = session.exec(
        select(RecoveryAttempt)
        .where(RecoveryAttempt.transaction_id == transaction_id)
        .order_by(RecoveryAttempt.created_at.desc())
    ).all()
    return attempts


@router.post("/seed")
def seed_transactions(session: Session = Depends(get_session)):
    return seed_sample_data(session)
