import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import Merchant, Transaction, TransactionStatus, RecoveryAttempt, RecoveryStatus
from app.schemas.recovery import RecoveryStrategy

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = {"payment.failed", "payment.captured", "order.paid", "payment_link.paid"}

PAYMENT_LINK_REFERENCE_PREFIX = "payrescue_"


class WebhookProcessingError(Exception):
    """Raised for any malformed or unprocessable webhook payload."""


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET is not configured — rejecting webhook")
        return False
    expected_signature = hmac.new(key=secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def extract_payment_entity(payload: dict) -> dict:
    try:
        return payload["payload"]["payment"]["entity"]
    except (KeyError, TypeError):
        raise WebhookProcessingError("Missing payment entity in webhook payload")


def extract_order_entity(payload: dict) -> Optional[dict]:
    return payload.get("payload", {}).get("order", {}).get("entity")


def extract_payment_link_entity(payload: dict) -> Optional[dict]:
    return payload.get("payload", {}).get("payment_link", {}).get("entity")


def extract_linked_transaction_id(entity: dict) -> Optional[int]:
    """
    Looks for the original PayRescue transaction ID a payment/payment-link
    entity is tied to: entity['notes']['payrescue_transaction_id'] first,
    then entity['reference_id'] formatted as 'payrescue_<id>'.
    """
    notes = entity.get("notes") or {}
    note_value = notes.get("payrescue_transaction_id")
    if note_value:
        try:
            return int(note_value)
        except (TypeError, ValueError):
            return None

    reference_id = entity.get("reference_id")
    if reference_id and reference_id.startswith(PAYMENT_LINK_REFERENCE_PREFIX):
        try:
            return int(reference_id[len(PAYMENT_LINK_REFERENCE_PREFIX):])
        except ValueError:
            return None

    return None


def get_or_create_default_merchant(session: Session) -> Merchant:
    merchant = session.exec(select(Merchant)).first()
    if merchant:
        return merchant
    merchant = Merchant(name="Default Merchant (auto-created)", razorpay_key_id="rzp_test_default")
    session.add(merchant)
    session.flush()
    logger.info("Auto-created default merchant for incoming webhook")
    return merchant


def get_transaction_by_order_id(session: Session, order_id: str) -> Optional[Transaction]:
    return session.exec(select(Transaction).where(Transaction.razorpay_order_id == order_id)).first()


def handle_linked_recovery_payment(session: Session, original_transaction_id: int, payload: dict) -> Optional[Transaction]:
    """
    Marks the original failed transaction 'recovered' when a payment tied
    to a PayRescue-generated payment link succeeds. Idempotent on redelivery.
    """
    transaction = session.get(Transaction, original_transaction_id)
    if transaction is None:
        logger.warning(f"Linked recovery payment referenced unknown transaction_id={original_transaction_id}")
        return None

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    new_payment_id = payment_entity.get("id")

    transaction.status = TransactionStatus.recovered
    if new_payment_id:
        transaction.razorpay_payment_id = new_payment_id
    transaction.raw_webhook_payload = payload
    transaction.updated_at = datetime.utcnow()

    pending_attempt = session.exec(
        select(RecoveryAttempt)
        .where(RecoveryAttempt.transaction_id == transaction.id)
        .where(RecoveryAttempt.strategy == RecoveryStrategy.payment_link.value)
        .where(RecoveryAttempt.status == RecoveryStatus.pending)
        .order_by(RecoveryAttempt.created_at.desc())
    ).first()
    if pending_attempt:
        pending_attempt.status = RecoveryStatus.success

    session.commit()
    session.refresh(transaction)
    logger.info(f"Transaction {transaction.id} marked recovered via linked payment-link payment")
    return transaction


def handle_payment_link_paid(session: Session, payload: dict) -> Optional[Transaction]:
    payment_link_entity = extract_payment_link_entity(payload)
    if payment_link_entity is None:
        raise WebhookProcessingError("payment_link.paid event missing payment_link entity")

    linked_transaction_id = extract_linked_transaction_id(payment_link_entity)
    if linked_transaction_id is None:
        raise WebhookProcessingError("payment_link.paid event missing a resolvable payrescue reference")

    return handle_linked_recovery_payment(session, linked_transaction_id, payload)


def handle_payment_failed(session: Session, payload: dict) -> Transaction:
    payment_entity = extract_payment_entity(payload)

    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    amount = payment_entity.get("amount")
    currency = payment_entity.get("currency", "INR")
    failure_reason = payment_entity.get("error_description") or payment_entity.get("error_code")

    if not order_id:
        raise WebhookProcessingError("payment.failed event missing order_id")
    if amount is None:
        raise WebhookProcessingError("payment.failed event missing amount")

    transaction = get_transaction_by_order_id(session, order_id)

    if transaction is None:
        merchant = get_or_create_default_merchant(session)
        transaction = Transaction(
            merchant_id=merchant.id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=TransactionStatus.failed,
            failure_reason=failure_reason,
            raw_webhook_payload=payload,
            updated_at=datetime.utcnow(),
        )
        session.add(transaction)
        logger.info(f"payment.failed: created transaction order_id={order_id}")
    else:
        transaction.razorpay_payment_id = payment_id or transaction.razorpay_payment_id
        transaction.status = TransactionStatus.failed
        transaction.failure_reason = failure_reason
        transaction.raw_webhook_payload = payload
        transaction.updated_at = datetime.utcnow()
        logger.info(f"payment.failed: updated transaction order_id={order_id}")

    session.commit()
    session.refresh(transaction)
    return transaction


def handle_payment_captured(session: Session, payload: dict) -> Optional[Transaction]:
    payment_entity = extract_payment_entity(payload)

    linked_transaction_id = extract_linked_transaction_id(payment_entity)
    if linked_transaction_id is not None:
        recovered = handle_linked_recovery_payment(session, linked_transaction_id, payload)
        if recovered is not None:
            return recovered

    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    amount = payment_entity.get("amount")
    currency = payment_entity.get("currency", "INR")

    if not order_id:
        raise WebhookProcessingError("payment.captured event missing order_id")
    if amount is None:
        raise WebhookProcessingError("payment.captured event missing amount")

    transaction = get_transaction_by_order_id(session, order_id)

    if transaction is None:
        merchant = get_or_create_default_merchant(session)
        transaction = Transaction(
            merchant_id=merchant.id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=TransactionStatus.captured,
            raw_webhook_payload=payload,
            updated_at=datetime.utcnow(),
        )
        session.add(transaction)
        logger.info(f"payment.captured: created transaction order_id={order_id}")
    else:
        transaction.razorpay_payment_id = payment_id or transaction.razorpay_payment_id
        transaction.status = TransactionStatus.captured
        transaction.raw_webhook_payload = payload
        transaction.updated_at = datetime.utcnow()
        logger.info(f"payment.captured: updated transaction order_id={order_id}")

    session.commit()
    session.refresh(transaction)
    return transaction


def handle_order_paid(session: Session, payload: dict) -> Optional[Transaction]:
    order_entity = extract_order_entity(payload) or {}
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    linked_transaction_id = extract_linked_transaction_id(order_entity) or extract_linked_transaction_id(payment_entity)
    if linked_transaction_id is not None:
        recovered = handle_linked_recovery_payment(session, linked_transaction_id, payload)
        if recovered is not None:
            return recovered

    order_id = order_entity.get("id") or payment_entity.get("order_id")
    if not order_id:
        raise WebhookProcessingError("order.paid event missing order_id")

    amount = order_entity.get("amount") or payment_entity.get("amount")
    currency = order_entity.get("currency") or payment_entity.get("currency", "INR")
    payment_id = payment_entity.get("id")

    transaction = get_transaction_by_order_id(session, order_id)

    if transaction is None:
        merchant = get_or_create_default_merchant(session)
        transaction = Transaction(
            merchant_id=merchant.id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=TransactionStatus.captured,
            raw_webhook_payload=payload,
            updated_at=datetime.utcnow(),
        )
        session.add(transaction)
        logger.info(f"order.paid: created transaction order_id={order_id}")
    else:
        transaction.status = TransactionStatus.captured
        if payment_id:
            transaction.razorpay_payment_id = payment_id
        transaction.raw_webhook_payload = payload
        transaction.updated_at = datetime.utcnow()
        logger.info(f"order.paid: confirmed transaction order_id={order_id}")

    session.commit()
    session.refresh(transaction)
    return transaction


def process_webhook_event(session: Session, payload: dict) -> dict:
    event_type = payload.get("event")
    if not event_type:
        raise WebhookProcessingError("Missing 'event' field in webhook payload")

    logger.info(f"Received Razorpay webhook: event={event_type}")

    if event_type not in SUPPORTED_EVENTS:
        logger.info(f"Ignoring unsupported event type: {event_type}")
        return {"status": "ignored", "event": event_type}

    if event_type == "payment.failed":
        transaction = handle_payment_failed(session, payload)
    elif event_type == "payment.captured":
        transaction = handle_payment_captured(session, payload)
    elif event_type == "order.paid":
        transaction = handle_order_paid(session, payload)
    else:
        transaction = handle_payment_link_paid(session, payload)

    if transaction is None:
        logger.warning(f"Event={event_type} could not be resolved to any transaction; acknowledging without changes")
        return {"status": "ignored", "event": event_type, "reason": "unresolvable reference"}

    logger.info(
        f"Processed event={event_type} order_id={transaction.razorpay_order_id} "
        f"payment_id={transaction.razorpay_payment_id} status={transaction.status.value}"
    )
    return {
        "status": "processed",
        "event": event_type,
        "transaction_id": transaction.id,
        "transaction_status": transaction.status.value,
    }
