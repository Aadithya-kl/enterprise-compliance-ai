"""
LangGraph workflow orchestration.

Graph topology:
  START
    -> retrieve_documents
      -> run_compliance_agent
        -> run_risk_agent
          -> run_report_agent
            -> persist_report
              -> END

State flows through the graph as a typed dict.
Each node is a pure function that accepts and returns state.
"""

from typing import Any, Optional, TypedDict

from app.agents.compliance_agent import ComplianceAgent
from app.agents.report_agent import ReportAgent
from app.agents.risk_agent import RiskAgent
from app.core.logging import get_logger
from app.services.rag_service import get_chunks_by_type

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class WorkflowState(TypedDict, total=False):
    """Typed state shared across all nodes in the workflow graph."""
    # Input
    policy_type: str
    regulation_type: str
    triggered_by_user_id: Optional[int]

    # Populated by retrieve_documents
    policy_chunks: list[str]
    regulation_chunks: list[str]

    # Populated by compliance agent
    compliance_analysis: dict

    # Populated by risk agent
    risk_assessment: dict

    # Populated by report agent
    final_report: dict

    # Populated by persist_report
    saved_report_id: Optional[int]

    # Set by any node on failure
    error: Optional[str]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

_compliance_agent = ComplianceAgent()
_risk_agent = RiskAgent()
_report_agent = ReportAgent()


def retrieve_documents(state: WorkflowState) -> WorkflowState:
    """Fetch policy and regulation chunks from ChromaDB."""
    policy_type = state.get("policy_type", "policy")
    regulation_type = state.get("regulation_type", "regulation")

    policy_chunks = get_chunks_by_type(policy_type)
    regulation_chunks = get_chunks_by_type(regulation_type)

    logger.info(
        f"[retrieve_documents] policy={len(policy_chunks)} chunks "
        f"regulation={len(regulation_chunks)} chunks"
    )

    if not policy_chunks:
        return {**state, "error": f"No documents of type '{policy_type}' found."}
    if not regulation_chunks:
        return {**state, "error": f"No documents of type '{regulation_type}' found."}

    return {**state, "policy_chunks": policy_chunks, "regulation_chunks": regulation_chunks}


def run_compliance_agent(state: WorkflowState) -> WorkflowState:
    """Execute the ComplianceAgent to produce a structured gap analysis."""
    if state.get("error"):
        return state   # Propagate error without executing

    result = _compliance_agent.run(state)

    if "error" in result:
        logger.error(f"[run_compliance_agent] {result['error']}")
        return {**state, "error": result["error"]}

    logger.info("[run_compliance_agent] complete")
    return {**state, **result}


def run_risk_agent(state: WorkflowState) -> WorkflowState:
    """Execute the RiskAgent to classify issues and build mitigation roadmap."""
    if state.get("error"):
        return state

    result = _risk_agent.run(state)

    if "error" in result:
        logger.error(f"[run_risk_agent] {result['error']}")
        return {**state, "error": result["error"]}

    logger.info("[run_risk_agent] complete")
    return {**state, **result}


def run_report_agent(state: WorkflowState) -> WorkflowState:
    """Execute the ReportAgent to synthesise the final audit report."""
    if state.get("error"):
        return state

    result = _report_agent.run(state)

    if "error" in result:
        logger.error(f"[run_report_agent] {result['error']}")
        return {**state, "error": result["error"]}

    logger.info("[run_report_agent] complete")
    return {**state, **result}


def persist_report(state: WorkflowState, db=None) -> WorkflowState:
    """
    Persist the final report to the database.
    db is injected at call time — not through LangGraph's state.
    """
    if state.get("error"):
        return state

    if not db:
        logger.warning("[persist_report] No db session provided — skipping persistence.")
        return state

    final_report: dict = state.get("final_report", {})
    if not final_report:
        return {**state, "error": "No final_report in state to persist."}

    from app.crud.audit_report import crud_audit_report

    # Map final_report fields to the audit_report schema
    report_dict = {
        "risk": final_report.get("risk_level", "Unknown"),
        "compliance_score": final_report.get("compliance_score", 0),
        "violation_count": final_report.get("total_violations", 0),
        "issues": final_report.get("issues", []),
        "recommendations": final_report.get("recommendations", []),
        "audit_timestamp": final_report.get("audit_timestamp", ""),
        "auditor": final_report.get("auditor", "Compliance AI Platform"),
    }

    saved = crud_audit_report.create_from_dict(
        db,
        report=report_dict,
        user_id=state.get("triggered_by_user_id"),
    )
    logger.info(f"[persist_report] Saved audit report id={saved.id}")
    return {**state, "saved_report_id": saved.id}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

try:
    from langgraph.graph import END, START, StateGraph

    def build_compliance_workflow() -> Any:
        """
        Construct and compile the LangGraph StateGraph.
        Returns a compiled graph that can be invoked with:
            graph.invoke(initial_state)
        """
        graph = StateGraph(WorkflowState)

        graph.add_node("retrieve_documents", retrieve_documents)
        graph.add_node("run_compliance_agent", run_compliance_agent)
        graph.add_node("run_risk_agent", run_risk_agent)
        graph.add_node("run_report_agent", run_report_agent)

        graph.add_edge(START, "retrieve_documents")
        graph.add_edge("retrieve_documents", "run_compliance_agent")
        graph.add_edge("run_compliance_agent", "run_risk_agent")
        graph.add_edge("run_risk_agent", "run_report_agent")
        graph.add_edge("run_report_agent", END)

        return graph.compile()

    _USE_LANGGRAPH = True
    logger.info("LangGraph workflow compiled successfully.")

except ImportError:
    logger.warning(
        "langgraph not installed. Falling back to sequential execution. "
        "Install with: pip install langgraph"
    )
    _USE_LANGGRAPH = False

    def build_compliance_workflow():
        """Fallback: sequential node execution without LangGraph."""
        return None


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------

def run_compliance_workflow(
    policy_type: str = "policy",
    regulation_type: str = "regulation",
    user_id: Optional[int] = None,
    db=None,
) -> WorkflowState:
    """
    Entry point for the compliance workflow.
    Runs the LangGraph graph if available, otherwise executes nodes sequentially.
    The persist_report node is always called with the db session directly,
    since LangGraph does not support injecting FastAPI dependencies into nodes.
    """
    initial_state: WorkflowState = {
        "policy_type": policy_type,
        "regulation_type": regulation_type,
        "triggered_by_user_id": user_id,
    }

    if _USE_LANGGRAPH:
        try:
            graph = build_compliance_workflow()
            state = graph.invoke(initial_state)
        except Exception as exc:
            logger.error(f"LangGraph execution failed: {exc}", exc_info=True)
            logger.info("Falling back to sequential node execution due to graph error...")
            state = retrieve_documents(initial_state)
            state = run_compliance_agent(state)
            state = run_risk_agent(state)
            state = run_report_agent(state)
    else:
        state = retrieve_documents(initial_state)
        state = run_compliance_agent(state)
        state = run_risk_agent(state)
        state = run_report_agent(state)

    # Persist separately so we can pass the db session
    if db is not None:
        try:
            state = persist_report(state, db=db)
        except Exception as exc:
            logger.error(f"Database persistence in workflow failed: {exc}", exc_info=True)
            state = {**state, "error": f"Database persistence failed: {exc}"}

    return state
