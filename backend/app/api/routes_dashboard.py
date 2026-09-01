from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.core.database import get_session
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(session: Session = Depends(get_session)):
    def count_by_status(status: TransactionStatus) -> int:
        query = select(func.count()).select_from(Transaction).where(Transaction.status == status)
        return session.exec(query).one()

    def sum_amount_by_status(status: TransactionStatus) -> int:
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.status == status
        )
        return session.exec(query).one()

    total_transactions = session.exec(select(func.count()).select_from(Transaction)).one()

    return DashboardSummary(
        total_transactions=total_transactions,
        total_failed=count_by_status(TransactionStatus.failed),
        total_captured=count_by_status(TransactionStatus.captured),
        total_recovered=count_by_status(TransactionStatus.recovered),
        revenue_at_risk=sum_amount_by_status(TransactionStatus.failed),
        revenue_recovered=sum_amount_by_status(TransactionStatus.recovered),
    )
