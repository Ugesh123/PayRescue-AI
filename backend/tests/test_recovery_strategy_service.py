from app.schemas.diagnosis import DiagnosisCategory, DiagnosisResult, RecommendedNextStep
from app.schemas.recovery import DecisionContext, RecoveryStrategy
from app.services.recovery_strategy_service import decide_recovery_strategy


def _diagnosis(category: DiagnosisCategory) -> DiagnosisResult:
    return DiagnosisResult(category=category, confidence=0.9, reason="test diagnosis",
                            recommended_next_step=RecommendedNextStep.manual_review)


def _context(amount: int = 50000, previous_attempts: int = 0) -> DecisionContext:
    return DecisionContext(amount=amount, currency="INR", diagnosis_category=DiagnosisCategory.unknown,
                            previous_recovery_attempts=previous_attempts)


def test_insufficient_funds_prefers_customer_update():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.insufficient_funds), _context())
    assert decision.strategy == RecoveryStrategy.customer_update_payment_method
    assert decision.requires_customer_action is True


def test_bank_timeout_prefers_retry_later():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.bank_timeout), _context())
    assert decision.strategy == RecoveryStrategy.retry_later


def test_bank_unavailable_prefers_retry_later():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.bank_unavailable), _context())
    assert decision.strategy == RecoveryStrategy.retry_later


def test_incorrect_otp_prefers_reauthentication():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.incorrect_otp), _context())
    assert decision.strategy == RecoveryStrategy.customer_reauthentication


def test_card_declined_prefers_alternate_method():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.card_declined), _context())
    assert decision.strategy == RecoveryStrategy.alternate_payment_method


def test_payment_limit_exceeded_prefers_customer_update():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.payment_limit_exceeded), _context())
    assert decision.strategy == RecoveryStrategy.customer_update_payment_method


def test_fraud_or_risk_always_escalates():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.fraud_or_risk_flag), _context())
    assert decision.strategy == RecoveryStrategy.escalate
    assert decision.requires_human_review is True


def test_customer_abandoned_prefers_reminder():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.customer_abandoned), _context())
    assert decision.strategy == RecoveryStrategy.reminder


def test_unknown_prefers_escalate():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.unknown), _context())
    assert decision.strategy == RecoveryStrategy.escalate


def test_high_value_transaction_favors_escalation():
    low_value = decide_recovery_strategy(_diagnosis(DiagnosisCategory.technical_error), _context(amount=50000))
    high_value = decide_recovery_strategy(_diagnosis(DiagnosisCategory.technical_error), _context(amount=2_000_000))
    high_escalate = next(c.score for c in high_value.candidate_strategies if c.strategy == RecoveryStrategy.escalate)
    low_escalate = next(c.score for c in low_value.candidate_strategies if c.strategy == RecoveryStrategy.escalate)
    assert high_escalate > low_escalate


def test_repeated_failures_reduce_retry_score():
    first = decide_recovery_strategy(_diagnosis(DiagnosisCategory.bank_timeout), _context(previous_attempts=0))
    repeated = decide_recovery_strategy(_diagnosis(DiagnosisCategory.bank_timeout), _context(previous_attempts=3))
    first_score = next(c.score for c in first.candidate_strategies if c.strategy == RecoveryStrategy.retry_later)
    repeated_score = next(c.score for c in repeated.candidate_strategies if c.strategy == RecoveryStrategy.retry_later)
    assert repeated_score < first_score


def test_fraud_never_selects_automatic_retry_strategy():
    decision = decide_recovery_strategy(_diagnosis(DiagnosisCategory.fraud_or_risk_flag), _context())
    automatic = {RecoveryStrategy.retry_same_route, RecoveryStrategy.retry_later, RecoveryStrategy.alternate_payment_method}
    assert decision.strategy not in automatic
    for candidate in decision.candidate_strategies:
        assert candidate.strategy not in automatic
