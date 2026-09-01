import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session

from app.models.transaction import Transaction
from app.models.recovery_attempt import RecoveryAttempt, RecoveryStatus
from app.schemas.recovery import RecoveryStrategy, RecoveryDecision
from app.schemas.execution import ExecutionResult, ExecutionStatus
from app.services.razorpay_client import create_payment_link, RazorpayClientError

logger = logging.getLogger(__name__)


def _record_recovery_attempt(
    session: Session, transaction_id: int, strategy: RecoveryStrategy, status: RecoveryStatus
) -> RecoveryAttempt:
    attempt = RecoveryAttempt(
        transaction_id=transaction_id,
        strategy=strategy.value,
        status=status,
        created_at=datetime.utcnow(),
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


def _execute_payment_link(session: Session, transaction: Transaction, decision: RecoveryDecision) -> ExecutionResult:
    try:
        payment_link_url = create_payment_link(
            amount=transaction.amount,
            currency=transaction.currency,
            description=f"Complete your payment for order {transaction.razorpay_order_id}",
            reference_id=f"payrescue_{transaction.id}",
            notes={"payrescue_transaction_id": str(transaction.id)},
        )
        attempt = _record_recovery_attempt(session, transaction.id, decision.strategy, RecoveryStatus.pending)
        return ExecutionResult(
            strategy=decision.strategy,
            execution_status=ExecutionStatus.success,
            action_taken="Generated a Razorpay payment link",
            message="Payment link generated successfully and ready to be shared with the customer",
            recovery_attempt_id=attempt.id,
            payment_link_url=payment_link_url,
            requires_customer_action=decision.requires_customer_action,
            requires_human_review=decision.requires_human_review,
        )
    except RazorpayClientError as exc:
        attempt = _record_recovery_attempt(session, transaction.id, decision.strategy, RecoveryStatus.failed)
        logger.warning(f"Payment link execution failed for transaction_id={transaction.id}: {exc}")
        return ExecutionResult(
            strategy=decision.strategy,
            execution_status=ExecutionStatus.failed,
            action_taken="Attempted to generate a Razorpay payment link",
            message="Payment link generation failed; this attempt has been recorded for review",
            recovery_attempt_id=attempt.id,
            payment_link_url=None,
            requires_customer_action=decision.requires_customer_action,
            requires_human_review=True,
        )


def _execute_escalate(
    session: Session, transaction: Transaction, decision: RecoveryDecision, override_reason: Optional[str] = None
) -> ExecutionResult:
    attempt = _record_recovery_attempt(session, transaction.id, RecoveryStrategy.escalate, RecoveryStatus.pending)

    evidence = {
        "transaction_id": transaction.id,
        "razorpay_order_id": transaction.razorpay_order_id,
        "razorpay_payment_id": transaction.razorpay_payment_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "failure_reason": transaction.failure_reason,
        "decision_reason": decision.reason,
        "override_reason": override_reason,
    }
    logger.info(f"Escalation evidence prepared for transaction_id={transaction.id}")

    return ExecutionResult(
        strategy=RecoveryStrategy.escalate,
        execution_status=ExecutionStatus.success,
        action_taken="Created an escalation record with evidence for merchant/support review",
        message=override_reason or "Escalated for human review",
        recovery_attempt_id=attempt.id,
        payment_link_url=None,
        requires_customer_action=False,
        requires_human_review=True,
        evidence=evidence,
    )


CUSTOMER_ACTION_MESSAGES: dict[RecoveryStrategy, str] = {
    RecoveryStrategy.reminder: "Reminder queued for the customer (simulated — no real message sent yet)",
    RecoveryStrategy.customer_update_payment_method:
        "Customer prompted to update their payment method (simulated — no real message sent yet)",
    RecoveryStrategy.customer_reauthentication:
        "Customer prompted to re-authenticate the payment (simulated — no real message sent yet)",
}


def _execute_customer_action(session: Session, transaction: Transaction, decision: RecoveryDecision) -> ExecutionResult:
    attempt = _record_recovery_attempt(session, transaction.id, decision.strategy, RecoveryStatus.pending)
    return ExecutionResult(
        strategy=decision.strategy,
        execution_status=ExecutionStatus.simulated,
        action_taken=f"Simulated {decision.strategy.value} notification (no real channel wired up yet)",
        message=CUSTOMER_ACTION_MESSAGES[decision.strategy],
        recovery_attempt_id=attempt.id,
        payment_link_url=None,
        requires_customer_action=True,
        requires_human_review=decision.requires_human_review,
    )


def _execute_alternate_payment_method(
    session: Session, transaction: Transaction, decision: RecoveryDecision
) -> ExecutionResult:
    attempt = _record_recovery_attempt(session, transaction.id, decision.strategy, RecoveryStatus.pending)
    return ExecutionResult(
        strategy=decision.strategy,
        execution_status=ExecutionStatus.simulated,
        action_taken="Simulated selection of an alternate payment route (e.g. switching from card to UPI)",
        message=(
            "Razorpay does not expose a direct API to force an alternate payment route on an "
            "existing order; this is a simulated decision only, pending a real routing mechanism"
        ),
        recovery_attempt_id=attempt.id,
        payment_link_url=None,
        requires_customer_action=decision.requires_customer_action,
        requires_human_review=decision.requires_human_review,
    )


def _execute_retry_scheduled(session: Session, transaction: Transaction, decision: RecoveryDecision) -> ExecutionResult:
    attempt = _record_recovery_attempt(session, transaction.id, decision.strategy, RecoveryStatus.pending)
    return ExecutionResult(
        strategy=decision.strategy,
        execution_status=ExecutionStatus.scheduled,
        action_taken=f"Recorded a {decision.strategy.value} intent — no charge has been attempted",
        message=(
            "Automatic retry charging is not yet implemented; this attempt records the intent "
            "so a future safe retry mechanism can pick it up"
        ),
        recovery_attempt_id=attempt.id,
        payment_link_url=None,
        requires_customer_action=False,
        requires_human_review=decision.requires_human_review,
    )


def _execute_no_action(session: Session, transaction: Transaction, decision: RecoveryDecision) -> ExecutionResult:
    attempt = _record_recovery_attempt(session, transaction.id, RecoveryStrategy.no_action, RecoveryStatus.success)
    return ExecutionResult(
        strategy=RecoveryStrategy.no_action,
        execution_status=ExecutionStatus.success,
        action_taken="No recovery action taken",
        message="Decision engine recommended no action at this time",
        recovery_attempt_id=attempt.id,
        payment_link_url=None,
        requires_customer_action=False,
        requires_human_review=False,
    )


def _execute_unsupported(session: Session, transaction: Transaction, decision: RecoveryDecision) -> ExecutionResult:
    attempt = _record_recovery_attempt(session, transaction.id, decision.strategy, RecoveryStatus.failed)
    logger.error(f"No execution handler registered for strategy={decision.strategy}")
    return ExecutionResult(
        strategy=decision.strategy,
        execution_status=ExecutionStatus.blocked,
        action_taken="No execution handler available for this strategy",
        message="This strategy is not yet supported for automatic execution",
        recovery_attempt_id=attempt.id,
        payment_link_url=None,
        requires_customer_action=False,
        requires_human_review=True,
    )


STRATEGY_HANDLERS = {
    RecoveryStrategy.payment_link: _execute_payment_link,
    RecoveryStrategy.escalate: _execute_escalate,
    RecoveryStrategy.reminder: _execute_customer_action,
    RecoveryStrategy.customer_update_payment_method: _execute_customer_action,
    RecoveryStrategy.customer_reauthentication: _execute_customer_action,
    RecoveryStrategy.alternate_payment_method: _execute_alternate_payment_method,
    RecoveryStrategy.retry_later: _execute_retry_scheduled,
    RecoveryStrategy.retry_same_route: _execute_retry_scheduled,
    RecoveryStrategy.no_action: _execute_no_action,
}


def execute_recovery(session: Session, transaction: Transaction, decision: RecoveryDecision) -> ExecutionResult:
    if decision.requires_human_review and decision.strategy != RecoveryStrategy.escalate:
        logger.warning(
            f"Overriding strategy '{decision.strategy.value}' to 'escalate' for "
            f"transaction_id={transaction.id} because requires_human_review is True"
        )
        return _execute_escalate(
            session, transaction, decision,
            override_reason=f"Original strategy '{decision.strategy.value}' was blocked pending human review",
        )

    handler = STRATEGY_HANDLERS.get(decision.strategy)
    if handler is None:
        return _execute_unsupported(session, transaction, decision)

    return handler(session, transaction, decision)
