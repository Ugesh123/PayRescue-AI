from enum import Enum
from typing import List

from pydantic import BaseModel


class AnomalySeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Anomaly(BaseModel):
    anomaly_detected: bool
    severity: AnomalySeverity
    pattern: str
    message: str
    affected_transaction_count: int
    recommended_action: str


class AnomalyReport(BaseModel):
    generated_at: str
    anomalies: List[Anomaly]
