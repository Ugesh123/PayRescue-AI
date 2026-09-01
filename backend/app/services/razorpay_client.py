import logging
from typing import Optional

import razorpay

from app.core.config import settings

logger = logging.getLogger(__name__)


class RazorpayClientError(Exception):
    """Raised when a Razorpay API call fails or the client is misconfigured."""


def _get_client() -> razorpay.Client:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise RazorpayClientError("Razorpay credentials are not configured")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def create_payment_link(
    *,
    amount: int,
    currency: str,
    description: str,
    reference_id: str,
    notes: Optional[dict] = None,
) -> str:
    """
    Creates a Razorpay Payment Link and returns its short_url.

    `reference_id` and `notes` both carry a stable pointer back to the
    original PayRescue transaction so a later webhook can identify which
    failed transaction just got recovered (closed-loop tracking).
    """
    client = _get_client()
    try:
        payload = {
            "amount": amount,
            "currency": currency,
            "description": description,
            "reference_id": reference_id,
            "notify": {"sms": False, "email": False},
            "reminder_enable": True,
        }
        if notes:
            payload["notes"] = notes

        response = client.payment_link.create(payload)
        short_url = response.get("short_url")
        if not short_url:
            raise RazorpayClientError("Razorpay response did not include a short_url")
        logger.info(f"Created Razorpay payment link for reference_id={reference_id}")
        return short_url
    except RazorpayClientError:
        raise
    except Exception as exc:
        logger.error(
            f"Razorpay payment link creation failed for reference_id={reference_id}: {type(exc).__name__}"
        )
        raise RazorpayClientError("Failed to create Razorpay payment link") from exc
