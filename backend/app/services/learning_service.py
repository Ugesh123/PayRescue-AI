from typing import Optional

from sqlmodel import Session, select

from app.models.transaction import Transaction, TransactionStatus
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.diagnosis import DiagnosisCategory
from app.schemas.recovery import RecoveryStrategy
from app.services.diagnosis_service import diagnose_transaction

MIN_SAMPLES_FOR_SIGNAL = 5


def get_strategy_performance_signal(
    session: Session, strategy: RecoveryStrategy, category: DiagnosisCategory
) -> Optional[float]:
    rows = session.exec(
        select(RecoveryAttempt.strategy, Transaction)
        .join(Transaction, Transaction.id == RecoveryAttempt.transaction_id)
        .where(RecoveryAttempt.strategy == strategy.value)
        .where(Transaction.status.in_([TransactionStatus.failed, TransactionStatus.recovered]))
    ).all()

    matching = [txn for _, txn in rows if diagnose_transaction(txn).category == category]

    if len(matching) < MIN_SAMPLES_FOR_SIGNAL:
        return None

    successes = sum(1 for txn in matching if txn.status == TransactionStatus.recovered)
    return round(successes / len(matching), 3)


def get_all_strategy_signals(session: Session, category: DiagnosisCategory) -> dict[RecoveryStrategy, float]:
    signals: dict[RecoveryStrategy, float] = {}
    for strategy in RecoveryStrategy:
        signal = get_strategy_performance_signal(session, strategy, category)
        if signal is not None:
            signals[strategy] = signal
    return signals
