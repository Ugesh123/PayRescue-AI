import random
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models import (
    Merchant,
    Transaction,
    TransactionStatus,
    RecoveryAttempt,
    RecoveryStatus,
)

FAILURE_REASONS = [
    "payment_failed: insufficient funds in account",
    "payment_failed: card declined by issuing bank",
    "payment_failed: issuer timeout, no response",
    "payment_failed: incorrect OTP entered",
    "payment_failed: bank server temporarily unavailable",
]

SAMPLE_MERCHANTS = [
    {"name": "Kirana Mart", "razorpay_key_id": "rzp_test_kiranamart"},
    {"name": "UrbanThreads Fashion", "razorpay_key_id": "rzp_test_urbanthreads"},
]


def seed_sample_data(session: Session) -> dict:
    """
    Creates sample merchants + a realistic mix of transactions for local
    development and demos. Safe to call multiple times.
    """
    merchants = []
    for m in SAMPLE_MERCHANTS:
        existing = session.exec(
            select(Merchant).where(Merchant.razorpay_key_id == m["razorpay_key_id"])
        ).first()
        if existing:
            merchants.append(existing)
            continue
        merchant = Merchant(name=m["name"], razorpay_key_id=m["razorpay_key_id"])
        session.add(merchant)
        session.flush()
        merchants.append(merchant)

    created_transactions = []

    def make_transaction(merchant, status, amount_rupees, failure_reason=None):
        order_id = f"order_{random.randint(100000, 999999)}"
        payment_id = (
            f"pay_{random.randint(100000, 999999)}"
            if status != TransactionStatus.created
            else None
        )
        txn = Transaction(
            merchant_id=merchant.id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            amount=amount_rupees * 100,
            currency="INR",
            status=status,
            failure_reason=failure_reason,
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
            updated_at=datetime.utcnow(),
        )
        session.add(txn)
        session.flush()
        return txn

    for merchant in merchants:
        created_transactions.append(make_transaction(merchant, TransactionStatus.created, 499))
        created_transactions.append(make_transaction(merchant, TransactionStatus.captured, 1299))
        created_transactions.append(make_transaction(merchant, TransactionStatus.captured, 2499))

        created_transactions.append(
            make_transaction(merchant, TransactionStatus.failed, 899, random.choice(FAILURE_REASONS))
        )
        created_transactions.append(
            make_transaction(merchant, TransactionStatus.failed, 3499, random.choice(FAILURE_REASONS))
        )

        recovered_txn = make_transaction(
            merchant, TransactionStatus.recovered, 1599, random.choice(FAILURE_REASONS)
        )
        session.add(
            RecoveryAttempt(
                transaction_id=recovered_txn.id,
                strategy="payment_link",
                status=RecoveryStatus.success,
                created_at=datetime.utcnow(),
            )
        )
        created_transactions.append(recovered_txn)

    session.commit()

    return {
        "merchants_seeded": len(merchants),
        "transactions_seeded": len(created_transactions),
    }
