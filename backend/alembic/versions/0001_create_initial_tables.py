"""create initial tables

Revision ID: 0001
Revises:
Create Date: 2026-08-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("razorpay_key_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_merchants_razorpay_key_id", "merchants", ["razorpay_key_id"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("razorpay_order_id", sa.String(length=255), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="created"),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("raw_webhook_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
    )
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_razorpay_order_id", "transactions", ["razorpay_order_id"])
    op.create_index("ix_transactions_razorpay_payment_id", "transactions", ["razorpay_payment_id"])
    op.create_index("ix_transactions_status", "transactions", ["status"])

    op.create_table(
        "recovery_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
    )
    op.create_index("ix_recovery_attempts_transaction_id", "recovery_attempts", ["transaction_id"])
    op.create_index("ix_recovery_attempts_status", "recovery_attempts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_recovery_attempts_status", table_name="recovery_attempts")
    op.drop_index("ix_recovery_attempts_transaction_id", table_name="recovery_attempts")
    op.drop_table("recovery_attempts")

    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_index("ix_transactions_razorpay_payment_id", table_name="transactions")
    op.drop_index("ix_transactions_razorpay_order_id", table_name="transactions")
    op.drop_index("ix_transactions_merchant_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_merchants_razorpay_key_id", table_name="merchants")
    op.drop_table("merchants")
