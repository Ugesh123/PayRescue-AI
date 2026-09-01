from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.schemas.anomaly import AnomalyReport
from app.schemas.analytics import RecoveryAnalytics
from app.services.anomaly_service import detect_anomalies
from app.services.analytics_service import compute_recovery_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/anomalies", response_model=AnomalyReport)
def get_anomalies(session: Session = Depends(get_session)):
    return detect_anomalies(session)


@router.get("/recovery", response_model=RecoveryAnalytics)
def get_recovery_analytics(session: Session = Depends(get_session)):
    return compute_recovery_analytics(session)
