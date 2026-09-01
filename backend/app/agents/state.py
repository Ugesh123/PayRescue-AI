from typing import Optional, TypedDict

from app.models.transaction import Transaction
from app.schemas.diagnosis import DiagnosisResult
from app.schemas.recovery import RecoveryDecision
from app.schemas.execution import ExecutionResult


class RecoveryAgentState(TypedDict, total=False):
    """
    Shared state threaded through the LangGraph pipeline. The DB Session
    is deliberately NOT part of this state - it's bound to each node via
    closures when the graph is built (see graph.py), since a session is
    request-scoped infrastructure, not agent memory.
    """
    transaction_id: int
    transaction: Optional[Transaction]
    diagnosis: Optional[DiagnosisResult]
    decision: Optional[RecoveryDecision]
    safety_blocked: bool
    safety_reason: Optional[str]
    execution_result: Optional[ExecutionResult]
    error: Optional[str]
