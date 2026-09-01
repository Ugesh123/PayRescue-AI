from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_transactions: int
    total_failed: int
    total_captured: int
    total_recovered: int
    revenue_at_risk: int      # paise
    revenue_recovered: int    # paise
