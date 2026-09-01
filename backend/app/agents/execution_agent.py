from sqlmodel import Session

from app.agents.state import RecoveryAgentState
from app.schemas.recovery import RecoveryStrategy
from app.services.recovery_execution_service import execute_recovery


def make_safety_node():
    """
    Makes the safety verdict a visible graph step. Does NOT duplicate
    enforcement - execute_recovery() still independently enforces the
    requires_human_review -> escalate override regardless of this node.
    """

    def safety_node(state: RecoveryAgentState) -> dict:
        if state.get("error"):
            return {}

        decision = state["decision"]
        if decision.requires_human_review and decision.strategy != RecoveryStrategy.escalate:
            return {
                "safety_blocked": True,
                "safety_reason": (
                    f"Strategy '{decision.strategy.value}' requires human review; "
                    "execution will be redirected to escalate"
                ),
            }
        return {"safety_blocked": False, "safety_reason": None}

    return safety_node


def make_execution_node(session: Session):
    """Thin LangGraph wrapper around execute_recovery() - no execution logic lives here."""

    def execution_node(state: RecoveryAgentState) -> dict:
        if state.get("error"):
            return {}
        result = execute_recovery(session, state["transaction"], state["decision"])
        return {"execution_result": result}

    return execution_node


def make_record_result_node():
    """Terminal node. The RecoveryAttempt row is already written inside execute_recovery()."""

    def record_result_node(state: RecoveryAgentState) -> dict:
        return {}

    return record_result_node
