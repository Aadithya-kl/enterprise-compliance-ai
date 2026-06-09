"""
Trend Analysis Workflow.
LangGraph orchestration for the Five-Year Trend Analysis feature.
"""

import time
import re
from typing import Optional, TypedDict, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from app.core.config import settings
from app.core.logging import get_logger
from app.services.rag_service import _collection

from app.agents.trend_agent import TrendAnalysisAgent, RiskTrendAgent, ExecutiveSummaryAgent

logger = get_logger(__name__)

class TrendWorkflowState(TypedDict, total=False):
    # Input
    triggered_by_user_id: Optional[int]
    query: Optional[str]

    # Populated by retrieve_trend_documents
    documents: list[dict]

    # Populated by agents
    trend_analysis: dict
    risk_trend: dict
    executive_summary: dict

    # Output
    final_trend_report: dict
    error: Optional[str]

_trend_agent = TrendAnalysisAgent()
_risk_agent = RiskTrendAgent()
_exec_agent = ExecutiveSummaryAgent()

def retrieve_trend_documents(state: TrendWorkflowState) -> TrendWorkflowState:
    t = time.monotonic()
    logger.info("[retrieve_trend_documents] ENTER")
    try:
        from app.services.rag_service import extract_filenames_from_query
        
        query = state.get("query")
        where_clause = None
        
        year_filter_start = None
        year_filter_end = None
        
        if query:
            q_lower = query.lower()
            # 1. Match range like "2010 to 2015" or "2010-2015" or "2010 and 2015"
            range_match = re.search(r'\b(19|20)\d{2}\s*(?:to|and|through|-)\s*(19|20)\d{2}\b', q_lower)
            if range_match:
                found_years = [int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b', range_match.group(0))]
                if len(found_years) == 2:
                    year_filter_start = min(found_years)
                    year_filter_end = max(found_years)
                    logger.info(f"[retrieve_trend_documents] parsed year range: {year_filter_start} - {year_filter_end}")
            else:
                # 2. Match "past X years" or "last X years"
                past_match = re.search(r'\b(?:past|last)\s+(\d+)\s+years?\b', q_lower)
                if past_match:
                    num_years = int(past_match.group(1))
                    import datetime
                    current_year = datetime.datetime.now().year
                    year_filter_start = current_year - num_years + 1
                    year_filter_end = current_year
                    logger.info(f"[retrieve_trend_documents] parsed relative years: past {num_years} years ({year_filter_start} - {year_filter_end})")

            # Fallback to standard filename match if no year range/relative filter is found
            if year_filter_start is None:
                all_meta = _collection.get(include=["metadatas"]).get("metadatas") or []
                target_fnames = extract_filenames_from_query(query, all_meta)
                logger.info(f"[retrieve_trend_documents] target_fnames: {target_fnames}")
                if target_fnames:
                    where_clause = {"filename": {"$in": target_fnames}}
                
        if where_clause:
            logger.info(f"[retrieve_trend_documents] using where_clause: {where_clause}")
            results = _collection.get(where=where_clause, include=["documents", "metadatas"])
        else:
            results = _collection.get(include=["documents", "metadatas"])
            
        docs = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        logger.info(f"[retrieve_trend_documents] retrieved {len(docs)} documents.")
        
        years_content = {}
        for doc, meta in zip(docs, metadatas):
            if not meta: continue
            fname = meta.get("filename") or meta.get("drive_file_name") or ""
            # Match years like 2020, 2021
            match = re.search(r'(19|20)\d{2}', fname)
            if match:
                year_str = match.group(0)
                year_val = int(year_str)
                # Apply filter bounds
                if year_filter_start is not None and year_filter_end is not None:
                    if not (year_filter_start <= year_val <= year_filter_end):
                        continue
                years_content.setdefault(year_str, []).append(doc)
                
        if not years_content:
            return {**state, "error": "No documents with years in their filename found for trend analysis."}
            
        documents = []
        for year in sorted(years_content.keys()):
            content = "\n\n".join(years_content[year])
            documents.append({"year": year, "content": content})
            
        logger.info(f"[retrieve_trend_documents] EXIT in {time.monotonic()-t:.2f}s — Found documents for years: {list(years_content.keys())}")
        return {**state, "documents": documents}
    except Exception as exc:
        logger.error(f"[retrieve_trend_documents] EXCEPTION: {exc}", exc_info=True)
        return {**state, "error": f"retrieve_trend_documents failed: {exc}"}

def run_trend_analysis_agent(state: TrendWorkflowState) -> TrendWorkflowState:
    if state.get("error"): return state
    try:
        result = _trend_agent.run(state)
        if "error" in result:
            return {**state, "error": result["error"]}
        return {**state, **result}
    except Exception as exc:
        return {**state, "error": f"run_trend_analysis_agent failed: {exc}"}

def run_risk_trend_agent(state: TrendWorkflowState) -> TrendWorkflowState:
    if state.get("error"): return state
    try:
        result = _risk_agent.run(state)
        if "error" in result:
            return {**state, "error": result["error"]}
        return {**state, **result}
    except Exception as exc:
        return {**state, "error": f"run_risk_trend_agent failed: {exc}"}

def run_executive_summary_agent(state: TrendWorkflowState) -> TrendWorkflowState:
    if state.get("error"): return state
    try:
        result = _exec_agent.run(state)
        if "error" in result:
            return {**state, "error": result["error"]}
        return {**state, **result}
    except Exception as exc:
        return {**state, "error": f"run_executive_summary_agent failed: {exc}"}

def format_trend_report(state: TrendWorkflowState) -> TrendWorkflowState:
    if state.get("error"): return state
    
    trend = state.get("trend_analysis", {})
    risk = state.get("risk_trend", {})
    exec_sum = state.get("executive_summary", {})
    
    final_report = {
        "quarterly_analysis": trend.get("quarterly_analysis", ""),
        "annual_analysis": trend.get("annual_analysis", ""),
        "five_year_analysis": trend.get("five_year_analysis", ""),
        "executive_summary": exec_sum.get("executive_summary", ""),
        "compliance_maturity_progression": exec_sum.get("compliance_maturity_progression", ""),
        "risk_evolution_summary": risk.get("risk_evolution_summary", "")
    }
    return {**state, "final_trend_report": final_report}

def _run_trend_sequential(initial_state: TrendWorkflowState) -> TrendWorkflowState:
    state = retrieve_trend_documents(initial_state)
    state = run_trend_analysis_agent(state)
    state = run_risk_trend_agent(state)
    state = run_executive_summary_agent(state)
    state = format_trend_report(state)
    return state

try:
    from langgraph.graph import StateGraph, START, END
    def build_trend_workflow():
        graph = StateGraph(TrendWorkflowState)
        graph.add_node("retrieve_trend_documents", retrieve_trend_documents)
        graph.add_node("run_trend_analysis_agent", run_trend_analysis_agent)
        graph.add_node("run_risk_trend_agent", run_risk_trend_agent)
        graph.add_node("run_executive_summary_agent", run_executive_summary_agent)
        graph.add_node("format_trend_report", format_trend_report)

        graph.add_edge(START, "retrieve_trend_documents")
        graph.add_edge("retrieve_trend_documents", "run_trend_analysis_agent")
        graph.add_edge("run_trend_analysis_agent", "run_risk_trend_agent")
        graph.add_edge("run_risk_trend_agent", "run_executive_summary_agent")
        graph.add_edge("run_executive_summary_agent", "format_trend_report")
        graph.add_edge("format_trend_report", END)

        return graph.compile()
    _USE_LANGGRAPH = True
except ImportError:
    _USE_LANGGRAPH = False

def run_trend_pipeline(user_id: Optional[int] = None, query: Optional[str] = None) -> TrendWorkflowState:
    timeout = settings.WORKFLOW_TIMEOUT_SECONDS * 2 # Trend analysis might take longer
    initial_state: TrendWorkflowState = {"triggered_by_user_id": user_id, "query": query}
    
    t_total = time.monotonic()
    logger.info(f"[trend_workflow] START — user_id={user_id} timeout={timeout}s")
    
    state = initial_state
    if _USE_LANGGRAPH:
        try:
            graph = build_trend_workflow()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(graph.invoke, initial_state)
                try:
                    state = future.result(timeout=timeout)
                except FutureTimeoutError:
                    future.cancel()
                    state = _run_trend_sequential(initial_state)
        except Exception:
            state = _run_trend_sequential(initial_state)
    else:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_trend_sequential, initial_state)
            try:
                state = future.result(timeout=timeout)
            except FutureTimeoutError:
                future.cancel()
                state = {**initial_state, "error": "Trend Workflow timed out."}
                
    elapsed = time.monotonic() - t_total
    if state.get("error"):
        logger.error(f"[trend_workflow] COMPLETE WITH ERROR in {elapsed:.2f}s: {state['error']}")
    else:
        logger.info(f"[trend_workflow] COMPLETE in {elapsed:.2f}s")
    return state
