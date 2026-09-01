from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import Session, select, func

from app.models.transaction import Transaction, TransactionStatus
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.anomaly import Anomaly, AnomalyReport, AnomalySeverity
from app.services.diagnosis_service import diagnose_transaction

RECENT_WINDOW_HOURS = 24
BASELINE_WINDOW_HOURS = 24
MIN_ANOMALY_COUNT = 5
SPIKE_MULTIPLIER = 2.0
CATEGORY_CONCENTRATION_THRESHOLD = 0.4
TIME_CONCENTRATION_THRESHOLD = 0.5
REPEATED_ATTEMPTS_THRESHOLD = 3

CATEGORY_RECOMMENDATIONS: dict[str, str] = {
    "bank_timeout": "Reduce automatic retries and favor alternate recovery until the bank stabilizes",
    "bank_unavailable": "Reduce automatic retries and favor alternate recovery until the bank stabilizes",
    "fraud_or_risk_flag": "Escalate all affected transactions for manual review immediately",
    "insufficient_funds": "Prioritize customer-facing payment-method-update flows over retries",
    "card_declined": "Prioritize alternate payment method and payment link flows over retries",
    "technical_error": "Investigate the payment gateway; hold off on further automatic retries",
}
DEFAULT_RECOMMENDATION = "Review affected transactions manually before continuing automatic recovery"


def _count_failed(session: Session, start: datetime, end: datetime) -> int:
    return session.exec(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.status == TransactionStatus.failed)
        .where(Transaction.created_at >= start)
        .where(Transaction.created_at < end)
    ).one()


def detect_failure_spike(session: Session) -> Optional[Anomaly]:
    now = datetime.utcnow()
    recent_start = now - timedelta(hours=RECENT_WINDOW_HOURS)
    baseline_start = recent_start - timedelta(hours=BASELINE_WINDOW_HOURS)

    recent_count = _count_failed(session, recent_start, now)
    if recent_count < MIN_ANOMALY_COUNT:
        return None

    baseline_count = _count_failed(session, baseline_start, recent_start)
    baseline_rate = max(baseline_count, 1)
    ratio = recent_count / baseline_rate

    if ratio < SPIKE_MULTIPLIER:
        return None

    severity = AnomalySeverity.high if ratio >= 3 else AnomalySeverity.medium
    return Anomaly(
        anomaly_detected=True,
        severity=severity,
        pattern="failure_spike",
        message=(
            f"Payment failures increased {ratio:.1f}x in the last {RECENT_WINDOW_HOURS}h "
            f"({recent_count} vs {baseline_count} in the prior {BASELINE_WINDOW_HOURS}h)"
        ),
        affected_transaction_count=recent_count,
        recommended_action="Reduce automatic retries and favor alternate recovery until failures normalize",
    )


def detect_category_spikes(session: Session) -> List[Anomaly]:
    now = datetime.utcnow()
    recent_start = now - timedelta(hours=RECENT_WINDOW_HOURS)

    recent_failed = session.exec(
        select(Transaction)
        .where(Transaction.status == TransactionStatus.failed)
        .where(Transaction.created_at >= recent_start)
    ).all()

    if len(recent_failed) < MIN_ANOMALY_COUNT:
        return []

    category_counts: dict[str, int] = {}
    for txn in recent_failed:
        category = diagnose_transaction(txn).category.value
        category_counts[category] = category_counts.get(category, 0) + 1

    total = len(recent_failed)
    anomalies: List[Anomaly] = []
    for category, count in category_counts.items():
        proportion = count / total
        if count >= MIN_ANOMALY_COUNT and proportion >= CATEGORY_CONCENTRATION_THRESHOLD:
            severity = AnomalySeverity.high if proportion >= 0.6 else AnomalySeverity.medium
            anomalies.append(
                Anomaly(
                    anomaly_detected=True,
                    severity=severity,
                    pattern=f"{category}_spike",
                    message=(
                        f"'{category}' accounts for {proportion:.0%} of failures in the last "
                        f"{RECENT_WINDOW_HOURS}h ({count} of {total})"
                    ),
                    affected_transaction_count=count,
                    recommended_action=CATEGORY_RECOMMENDATIONS.get(category, DEFAULT_RECOMMENDATION),
                )
            )
    return anomalies


def detect_time_concentration(session: Session) -> Optional[Anomaly]:
    now = datetime.utcnow()
    recent_start = now - timedelta(hours=RECENT_WINDOW_HOURS)

    timestamps = session.exec(
        select(Transaction.created_at)
        .where(Transaction.status == TransactionStatus.failed)
        .where(Transaction.created_at >= recent_start)
    ).all()

    if len(timestamps) < MIN_ANOMALY_COUNT:
        return None

    bucket_counts: dict[int, int] = {}
    for created_at in timestamps:
        bucket = int((created_at - recent_start).total_seconds() // 3600)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    busiest_count = max(bucket_counts.values())
    total = len(timestamps)
    proportion = busiest_count / total

    if busiest_count >= MIN_ANOMALY_COUNT and proportion >= TIME_CONCENTRATION_THRESHOLD:
        return Anomaly(
            anomaly_detected=True,
            severity=AnomalySeverity.high if proportion >= 0.7 else AnomalySeverity.medium,
            pattern="failure_time_concentration",
            message=(
                f"{proportion:.0%} of recent failures ({busiest_count} of {total}) occurred within "
                "a single 1-hour window, suggesting a short outage or burst"
            ),
            affected_transaction_count=busiest_count,
            recommended_action="Investigate for a time-bound outage before continuing automatic retries",
        )
    return None


def detect_repeated_failure_transactions(session: Session) -> Optional[Anomaly]:
    rows = session.exec(
        select(RecoveryAttempt.transaction_id, func.count())
        .group_by(RecoveryAttempt.transaction_id)
        .having(func.count() >= REPEATED_ATTEMPTS_THRESHOLD)
    ).all()

    if not rows:
        return None

    affected_count = len(rows)
    return Anomaly(
        anomaly_detected=True,
        severity=AnomalySeverity.medium,
        pattern="repeated_recovery_failures",
        message=(
            f"{affected_count} transaction(s) have {REPEATED_ATTEMPTS_THRESHOLD}+ recovery attempts "
            "without resolution, suggesting the chosen strategies aren't working for these cases"
        ),
        affected_transaction_count=affected_count,
        recommended_action="Escalate these transactions to human review instead of further automatic attempts",
    )


def detect_anomalies(session: Session) -> AnomalyReport:
    anomalies: List[Anomaly] = []

    spike = detect_failure_spike(session)
    if spike:
        anomalies.append(spike)

    anomalies.extend(detect_category_spikes(session))

    time_anomaly = detect_time_concentration(session)
    if time_anomaly:
        anomalies.append(time_anomaly)

    repeated = detect_repeated_failure_transactions(session)
    if repeated:
        anomalies.append(repeated)

    return AnomalyReport(generated_at=datetime.utcnow().isoformat(), anomalies=anomalies)
