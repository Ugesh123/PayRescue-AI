from app.agents.state import RecoveryAgentState
from app.services.diagnosis_service import diagnose_transaction


def make_diagnosis_node():
    """Thin LangGraph wrapper around diagnose_transaction() - no diagnosis logic lives here."""

    def diagnosis_node(state: RecoveryAgentState) -> dict:
        if state.get("error"):
            return {}
        diagnosis = diagnose_transaction(state["transaction"])
        return {"diagnosis": diagnosis}

    return diagnosis_node
