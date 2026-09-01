import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.services.webhook_service import (
    verify_webhook_signature,
    process_webhook_event,
    WebhookProcessingError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(request: Request, session: Session = Depends(get_session)):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        logger.warning("Webhook rejected: missing X-Razorpay-Signature header")
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    if not verify_webhook_signature(raw_body, signature, settings.razorpay_webhook_secret):
        logger.warning("Webhook rejected: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("Webhook rejected: invalid JSON body")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        result = process_webhook_event(session, payload)
    except WebhookProcessingError as exc:
        logger.warning(f"Webhook processing error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    return result
