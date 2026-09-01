from langgraph.graph import StateGraph, START, END
from sqlmodel import Session

from app.agents.state import RecoveryAgentState
from app.agents.diagnosis_agent import make_diagnosis_node
from app.agents.strategy_agent import make_strategy_node
from app.agents.execution_agent import make_safety_node, make_execution_node, make_record_result_node
from app.models.transaction import Transaction


def _make_load_transaction_node(session: Session):
    def load_transaction(state: RecoveryAgentState) -> dict:
        transaction = session.get(Transaction, state["transaction_id"])
        if transaction is None:
            return {"error": f"Transaction {state['transaction_id']} not found"}
        return {"transaction": transaction}

    return load_transaction


def build_recovery_graph(session: Session):
    """
    Orchestration ONLY: every node is a thin wrapper calling an existing
    service function (diagnose_transaction, decide_recovery_strategy,
    execute_recovery). No business logic is duplicated here.

    START -> load_transaction -> diagnosis -> strategy -> safety_check
          -> execution -> record_result -> END
    """
    graph = StateGraph(RecoveryAgentState)

    graph.add_node("load_transaction", _make_load_transaction_node(session))
    graph.add_node("diagnosis", make_diagnosis_node())
    graph.add_node("strategy", make_strategy_node(session))
    graph.add_node("safety_check", make_safety_node())
    graph.add_node("execution", make_execution_node(session))
    graph.add_node("record_result", make_record_result_node())

    graph.add_edge(START, "load_transaction")
    graph.add_edge("load_transaction", "diagnosis")
    graph.add_edge("diagnosis", "strategy")
    graph.add_edge("strategy", "safety_check")
    graph.add_edge("safety_check", "execution")
    graph.add_edge("execution", "record_result")
    graph.add_edge("record_result", END)

    return graph.compile()
