from sqlmodel import Session, select, func

from app.agents.state import RecoveryAgentState
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.recovery import DecisionContext
from app.services.recovery_strategy_service import decide_recovery_strategy
from app.services.learning_service import get_all_strategy_signals


def make_strategy_node(session: Session):
    """Thin LangGraph wrapper around decide_recovery_strategy() plus the learning-loop lookup."""

    def strategy_node(state: RecoveryAgentState) -> dict:
        if state.get("error"):
            return {}

        transaction = state["transaction"]
        diagnosis = state["diagnosis"]

        previous_attempts_count = session.exec(
            select(func.count())
            .select_from(RecoveryAttempt)
            .where(RecoveryAttempt.transaction_id == transaction.id)
        ).one()

        context = DecisionContext(
            amount=transaction.amount,
            currency=transaction.currency,
            diagnosis_category=diagnosis.category,
            previous_recovery_attempts=previous_attempts_count,
        )
        historical_signals = get_all_strategy_signals(session, diagnosis.category)

        decision = decide_recovery_strategy(diagnosis, context, historical_signals)
        return {"decision": decision}

    return strategy_node
