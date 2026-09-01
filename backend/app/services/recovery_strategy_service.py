from typing import List, Optional

from app.schemas.diagnosis import DiagnosisCategory, DiagnosisResult
from app.schemas.recovery import (
    RecoveryStrategy,
    Urgency,
    DecisionContext,
    CandidateStrategy,
    RecoveryDecision,
)

AGGRESSIVE_AUTOMATIC_STRATEGIES = {
    RecoveryStrategy.retry_same_route,
    RecoveryStrategy.retry_later,
    RecoveryStrategy.alternate_payment_method,
}

CUSTOMER_ACTION_STRATEGIES = {
    RecoveryStrategy.customer_reauthentication,
    RecoveryStrategy.customer_update_payment_method,
    RecoveryStrategy.payment_link,
    RecoveryStrategy.reminder,
}

HUMAN_REVIEW_STRATEGIES = {RecoveryStrategy.escalate}

HIGH_VALUE_THRESHOLD_PAISE = 1_000_000  # ₹10,000
HISTORICAL_WEIGHT = 0.3

CANDIDATE_CONFIG: dict[DiagnosisCategory, List[dict]] = {
    DiagnosisCategory.insufficient_funds: [
        {"strategy": RecoveryStrategy.customer_update_payment_method, "base_score": 0.80, "base_probability": 0.60,
         "reason": "Funds issue — ask customer to update or use a different payment method"},
        {"strategy": RecoveryStrategy.reminder, "base_score": 0.40, "base_probability": 0.30,
         "reason": "Gentle reminder in case funds become available later"},
    ],
    DiagnosisCategory.bank_timeout: [
        {"strategy": RecoveryStrategy.retry_later, "base_score": 0.85, "base_probability": 0.70,
         "reason": "Likely transient bank timeout; retrying later has a good chance of success"},
        {"strategy": RecoveryStrategy.alternate_payment_method, "base_score": 0.50, "base_probability": 0.55,
         "reason": "Fallback if a retry on the same route fails again"},
    ],
    DiagnosisCategory.bank_unavailable: [
        {"strategy": RecoveryStrategy.retry_later, "base_score": 0.80, "base_probability": 0.65,
         "reason": "Bank/gateway outages are usually temporary"},
        {"strategy": RecoveryStrategy.payment_link, "base_score": 0.45, "base_probability": 0.50,
         "reason": "Useful fallback if the outage persists"},
    ],
    DiagnosisCategory.incorrect_otp: [
        {"strategy": RecoveryStrategy.customer_reauthentication, "base_score": 0.85, "base_probability": 0.75,
         "reason": "OTP entry issue needs a fresh authentication attempt"},
        {"strategy": RecoveryStrategy.reminder, "base_score": 0.30, "base_probability": 0.25,
         "reason": "Low-friction nudge if the customer doesn't act immediately"},
    ],
    DiagnosisCategory.card_declined: [
        {"strategy": RecoveryStrategy.alternate_payment_method, "base_score": 0.75, "base_probability": 0.60,
         "reason": "A different payment method may bypass the issuing bank's decline"},
        {"strategy": RecoveryStrategy.customer_update_payment_method, "base_score": 0.60, "base_probability": 0.50,
         "reason": "Customer may need to use a different card"},
        {"strategy": RecoveryStrategy.payment_link, "base_score": 0.40, "base_probability": 0.45,
         "reason": "Fallback link letting the customer retry with any method"},
    ],
    DiagnosisCategory.payment_limit_exceeded: [
        {"strategy": RecoveryStrategy.customer_update_payment_method, "base_score": 0.75, "base_probability": 0.55,
         "reason": "Customer likely needs a payment method under their available limit"},
        {"strategy": RecoveryStrategy.payment_link, "base_score": 0.50, "base_probability": 0.45,
         "reason": "Lets the customer retry at their convenience with another method"},
    ],
    DiagnosisCategory.authentication_failure: [
        {"strategy": RecoveryStrategy.customer_reauthentication, "base_score": 0.80, "base_probability": 0.65,
         "reason": "3D Secure / authentication step needs to be redone"},
    ],
    DiagnosisCategory.technical_error: [
        {"strategy": RecoveryStrategy.retry_later, "base_score": 0.70, "base_probability": 0.55,
         "reason": "Gateway-side technical errors are often transient"},
        {"strategy": RecoveryStrategy.escalate, "base_score": 0.35, "base_probability": 0.30,
         "reason": "Escalate if the technical error persists across attempts"},
    ],
    DiagnosisCategory.fraud_or_risk_flag: [
        {"strategy": RecoveryStrategy.escalate, "base_score": 0.95, "base_probability": 0.20,
         "reason": "Fraud/risk flags always require human review, never automatic recovery"},
    ],
    DiagnosisCategory.customer_abandoned: [
        {"strategy": RecoveryStrategy.reminder, "base_score": 0.70, "base_probability": 0.40,
         "reason": "Customer left voluntarily; a reminder is the least intrusive nudge"},
        {"strategy": RecoveryStrategy.payment_link, "base_score": 0.55, "base_probability": 0.40,
         "reason": "A fresh link makes it easy for the customer to complete the purchase"},
    ],
    DiagnosisCategory.unknown: [
        {"strategy": RecoveryStrategy.escalate, "base_score": 0.60, "base_probability": 0.30,
         "reason": "Insufficient signal to safely automate; needs human review"},
        {"strategy": RecoveryStrategy.payment_link, "base_score": 0.40, "base_probability": 0.35,
         "reason": "Low-risk fallback that doesn't require understanding the failure cause"},
    ],
}

NEXT_STEP_TEXT: dict[RecoveryStrategy, str] = {
    RecoveryStrategy.retry_same_route: "Queue an automatic retry on the same payment route",
    RecoveryStrategy.retry_later: "Queue a delayed automatic retry",
    RecoveryStrategy.alternate_payment_method: "Attempt recovery via an alternate payment route",
    RecoveryStrategy.payment_link: "Generate and send a fresh payment link to the customer",
    RecoveryStrategy.customer_reauthentication: "Prompt the customer to re-authenticate the payment",
    RecoveryStrategy.customer_update_payment_method: "Ask the customer to update or replace their payment method",
    RecoveryStrategy.reminder: "Send a low-friction reminder to the customer",
    RecoveryStrategy.escalate: "Escalate to human review before any recovery action",
    RecoveryStrategy.no_action: "No recovery action recommended at this time",
}


def generate_candidate_strategies(diagnosis: DiagnosisResult) -> List[dict]:
    return CANDIDATE_CONFIG.get(diagnosis.category, CANDIDATE_CONFIG[DiagnosisCategory.unknown])


def score_strategy(
    candidate: dict,
    diagnosis: DiagnosisResult,
    context: DecisionContext,
    historical_signals: Optional[dict[RecoveryStrategy, float]] = None,
) -> CandidateStrategy:
    historical_signals = historical_signals or {}
    strategy = candidate["strategy"]
    score = candidate["base_score"]
    probability = candidate["base_probability"]
    reasons = [candidate["reason"]]

    if context.amount >= HIGH_VALUE_THRESHOLD_PAISE and strategy in AGGRESSIVE_AUTOMATIC_STRATEGIES:
        score *= 0.7
        reasons.append("Score reduced: high transaction value favors human review over automatic action")
    if context.amount >= HIGH_VALUE_THRESHOLD_PAISE and strategy == RecoveryStrategy.escalate:
        score = min(1.0, score + 0.15)
        reasons.append("Score increased: high transaction value favors escalation to human review")

    if context.previous_recovery_attempts >= 1 and strategy in AGGRESSIVE_AUTOMATIC_STRATEGIES:
        penalty = min(0.1 * context.previous_recovery_attempts, 0.4)
        score = max(0.0, score - penalty)
        probability = max(0.0, probability - penalty)
        reasons.append(
            f"Score reduced: {context.previous_recovery_attempts} prior recovery attempt(s) "
            "lower confidence in repeating an automatic retry"
        )
    if context.previous_recovery_attempts >= 2 and strategy == RecoveryStrategy.escalate:
        score = min(1.0, score + 0.2)
        reasons.append("Score increased: repeated failures favor escalation over further automation")

    if strategy in historical_signals:
        historical_rate = historical_signals[strategy]
        score = (1 - HISTORICAL_WEIGHT) * score + HISTORICAL_WEIGHT * historical_rate
        probability = (1 - HISTORICAL_WEIGHT) * probability + HISTORICAL_WEIGHT * historical_rate
        reasons.append(
            f"Adjusted using historical performance: succeeded {historical_rate:.0%} of the time "
            "for similar failures in the past"
        )

    if diagnosis.category == DiagnosisCategory.fraud_or_risk_flag and strategy in AGGRESSIVE_AUTOMATIC_STRATEGIES:
        score = 0.0
        probability = 0.0
        reasons.append("Blocked: automatic retry strategies are never allowed for fraud/risk flags")

    return CandidateStrategy(
        strategy=strategy,
        score=round(min(max(score, 0.0), 1.0), 2),
        estimated_success_probability=round(min(max(probability, 0.0), 1.0), 2),
        reason=" | ".join(reasons),
    )


def select_best_strategy(scored_candidates: List[CandidateStrategy]) -> CandidateStrategy:
    return max(scored_candidates, key=lambda c: c.score)


def _determine_urgency(diagnosis: DiagnosisResult, context: DecisionContext) -> Urgency:
    if diagnosis.category == DiagnosisCategory.fraud_or_risk_flag:
        return Urgency.high
    if context.amount >= HIGH_VALUE_THRESHOLD_PAISE:
        return Urgency.high
    if diagnosis.category in {
        DiagnosisCategory.bank_timeout,
        DiagnosisCategory.bank_unavailable,
        DiagnosisCategory.technical_error,
    }:
        return Urgency.medium
    return Urgency.low


def decide_recovery_strategy(
    diagnosis: DiagnosisResult,
    context: DecisionContext,
    historical_signals: Optional[dict[RecoveryStrategy, float]] = None,
) -> RecoveryDecision:
    raw_candidates = generate_candidate_strategies(diagnosis)
    scored_candidates = [
        score_strategy(c, diagnosis, context, historical_signals) for c in raw_candidates
    ]
    winner = select_best_strategy(scored_candidates)

    return RecoveryDecision(
        strategy=winner.strategy,
        confidence=winner.score,
        reason=winner.reason,
        urgency=_determine_urgency(diagnosis, context),
        estimated_success_probability=winner.estimated_success_probability,
        requires_customer_action=winner.strategy in CUSTOMER_ACTION_STRATEGIES,
        requires_human_review=(
            winner.strategy in HUMAN_REVIEW_STRATEGIES
            or diagnosis.category == DiagnosisCategory.fraud_or_risk_flag
        ),
        next_step=NEXT_STEP_TEXT[winner.strategy],
        candidate_strategies=scored_candidates,
    )
