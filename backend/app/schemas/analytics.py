from typing import List, Optional

from pydantic import BaseModel


class StrategyPerformance(BaseModel):
    strategy: str
    total_attempts: int
    successful_attempts: int
    success_rate: float


class CategoryPerformance(BaseModel):
    category: str
    total_failed: int
    total_recovered: int
    recovery_rate: float


class RecoveryAnalytics(BaseModel):
    total_failed: int
    total_recovered: int
    recovery_rate: float
    revenue_at_risk: int
    revenue_recovered: int
    total_recovery_attempts: int
    average_attempts_per_recovered_transaction: float
    most_successful_strategy: Optional[str]
    strategy_performance: List[StrategyPerformance]
    category_performance: List[CategoryPerformance]
