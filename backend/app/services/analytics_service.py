from typing import List, Optional

from sqlmodel import Session, select, func

from app.models.transaction import Transaction, TransactionStatus
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.analytics import RecoveryAnalytics, StrategyPerformance, CategoryPerformance
from app.services.diagnosis_service import diagnose_transaction


def _strategy_performance(session: Session) -> List[StrategyPerformance]:
    rows = session.exec(
        select(RecoveryAttempt.strategy, Transaction.status)
        .join(Transaction, Transaction.id == RecoveryAttempt.transaction_id)
        .where(RecoveryAttempt.strategy.is_not(None))
    ).all()

    totals: dict[str, int] = {}
    successes: dict[str, int] = {}
    for strategy, txn_status in rows:
        totals[strategy] = totals.get(strategy, 0) + 1
        if txn_status == TransactionStatus.recovered:
            successes[strategy] = successes.get(strategy, 0) + 1

    performance = [
        StrategyPerformance(
            strategy=strategy,
            total_attempts=total,
            successful_attempts=successes.get(strategy, 0),
            success_rate=round(successes.get(strategy, 0) / total, 3) if total else 0.0,
        )
        for strategy, total in totals.items()
    ]
    return sorted(performance, key=lambda p: p.total_attempts, reverse=True)


def _category_performance(session: Session) -> List[CategoryPerformance]:
    transactions = session.exec(
        select(Transaction).where(
            Transaction.status.in_([TransactionStatus.failed, TransactionStatus.recovered])
        )
    ).all()

    totals: dict[str, int] = {}
    recovered: dict[str, int] = {}
    for txn in transactions:
        category = diagnose_transaction(txn).category.value
        totals[category] = totals.get(category, 0) + 1
        if txn.status == TransactionStatus.recovered:
            recovered[category] = recovered.get(category, 0) + 1

    performance = [
        CategoryPerformance(
            category=category,
            total_failed=total,
            total_recovered=recovered.get(category, 0),
            recovery_rate=round(recovered.get(category, 0) / total, 3) if total else 0.0,
        )
        for category, total in totals.items()
    ]
    return sorted(performance, key=lambda p: p.total_failed, reverse=True)


def compute_recovery_analytics(session: Session) -> RecoveryAnalytics:
    total_failed = session.exec(
        select(func.count()).select_from(Transaction).where(Transaction.status == TransactionStatus.failed)
    ).one()
    total_recovered = session.exec(
        select(func.count()).select_from(Transaction).where(Transaction.status == TransactionStatus.recovered)
    ).one()
    revenue_at_risk = session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.status == TransactionStatus.failed)
    ).one()
    revenue_recovered = session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.status == TransactionStatus.recovered)
    ).one()
    total_recovery_attempts = session.exec(select(func.count()).select_from(RecoveryAttempt)).one()

    recovery_pool = total_failed + total_recovered
    recovery_rate = round(total_recovered / recovery_pool, 3) if recovery_pool else 0.0
    average_attempts_per_recovered = (
        round(total_recovery_attempts / total_recovered, 2) if total_recovered else 0.0
    )

    strategy_performance = _strategy_performance(session)
    most_successful_strategy: Optional[str] = None
    if strategy_performance:
        most_successful_strategy = max(strategy_performance, key=lambda s: s.success_rate).strategy

    return RecoveryAnalytics(
        total_failed=total_failed,
        total_recovered=total_recovered,
        recovery_rate=recovery_rate,
        revenue_at_risk=revenue_at_risk,
        revenue_recovered=revenue_recovered,
        total_recovery_attempts=total_recovery_attempts,
        average_attempts_per_recovered_transaction=average_attempts_per_recovered,
        most_successful_strategy=most_successful_strategy,
        strategy_performance=strategy_performance,
        category_performance=_category_performance(session),
    )
