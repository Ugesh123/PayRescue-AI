"""
Local development utility: builds a valid, correctly-signed Razorpay-style
webhook payload for manual testing, so /webhooks/razorpay can be exercised
without a real Razorpay account or live delivery.

This file is NOT imported by any app code - it's a standalone script.

Usage:
    python scripts/simulate_webhook.py payment.failed
    python scripts/simulate_webhook.py payment.captured
    python scripts/simulate_webhook.py order.paid
"""
import hashlib
import hmac
import json
import sys

from app.core.config import settings

SAMPLE_PAYLOADS = {
    "payment.failed": {
        "entity": "event",
        "account_id": "acc_test_local",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_TESTFAIL001",
                    "order_id": "order_TESTORDER001",
                    "amount": 89900,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed due to insufficient funds in the customer's bank account.",
                }
            }
        },
        "created_at": 1735300000,
    },
    "payment.captured": {
        "entity": "event",
        "account_id": "acc_test_local",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_TESTCAP001",
                    "order_id": "order_TESTORDER002",
                    "amount": 129900,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
        "created_at": 1735300100,
    },
    "order.paid": {
        "entity": "event",
        "account_id": "acc_test_local",
        "event": "order.paid",
        "contains": ["payment", "order"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_TESTCAP001",
                    "order_id": "order_TESTORDER002",
                    "amount": 129900,
                    "currency": "INR",
                    "status": "captured",
                }
            },
            "order": {
                "entity": {
                    "id": "order_TESTORDER002",
                    "amount": 129900,
                    "currency": "INR",
                    "status": "paid",
                }
            },
        },
        "created_at": 1735300150,
    },
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SAMPLE_PAYLOADS:
        print(f"Usage: python scripts/simulate_webhook.py <{'|'.join(SAMPLE_PAYLOADS)}>")
        sys.exit(1)

    event_type = sys.argv[1]
    payload = SAMPLE_PAYLOADS[event_type]
    raw_body = json.dumps(payload).encode("utf-8")

    signature = hmac.new(
        key=settings.razorpay_webhook_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    print("Payload JSON:\n")
    print(raw_body.decode("utf-8"))
    print("\nComputed X-Razorpay-Signature:\n")
    print(signature)
    print("\nEquivalent curl command:\n")
    print(
        f"curl -X POST http://localhost:8000/webhooks/razorpay "
        f"-H 'Content-Type: application/json' "
        f"-H 'X-Razorpay-Signature: {signature}' "
        f"-d '{raw_body.decode('utf-8')}'"
    )


if __name__ == "__main__":
    main()
