"""
LangGraph orchestration of the extraction pipeline:

    ingest -> classify -> extract -> qa_validate -> [store | flag_for_review]

Each node only touches its own slice of the shared state, which is what
lets you swap in a different extractor, add a node, or change the QA
rules without rewriting the graph's control flow.
"""

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from extractor import get_extractor
from qa import validate
from schema import DocumentExtraction, QAResult


class PipelineState(TypedDict):
    document_id: str
    raw_text: str
    category_hint: Optional[str]
    extraction: Optional[DocumentExtraction]
    qa_result: Optional[QAResult]
    status: Optional[str]  # "stored" | "flagged"


_extractor = get_extractor()


def ingest_node(state: PipelineState) -> PipelineState:
    # In a real deployment this would read from disk/S3/a queue; here the
    # raw_text is already provided by the caller. Kept as its own node so
    # ingestion-time concerns (encoding, size limits) have a clear home.
    return state


def classify_node(state: PipelineState) -> PipelineState:
    # A cheap pre-classification hint could route documents to different
    # extractor configurations; left as a pass-through for the heuristic/
    # generic-LLM backends, but this is the seam where that would plug in.
    return state


def extract_node(state: PipelineState) -> PipelineState:
    extraction = _extractor.extract(state["document_id"], state["raw_text"])
    return {**state, "extraction": extraction}


def qa_validate_node(state: PipelineState) -> PipelineState:
    qa_result = validate(state["extraction"])
    return {**state, "qa_result": qa_result}


def store_node(state: PipelineState) -> PipelineState:
    return {**state, "status": "stored"}


def flag_node(state: PipelineState) -> PipelineState:
    return {**state, "status": "flagged"}


def route_after_qa(state: PipelineState) -> str:
    return "store" if state["qa_result"].passed else "flag"


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("qa_validate", qa_validate_node)
    graph.add_node("store", store_node)
    graph.add_node("flag", flag_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "classify")
    graph.add_edge("classify", "extract")
    graph.add_edge("extract", "qa_validate")
    graph.add_conditional_edges("qa_validate", route_after_qa, {"store": "store", "flag": "flag"})
    graph.add_edge("store", END)
    graph.add_edge("flag", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_pipeline(document_id: str, raw_text: str) -> PipelineState:
    graph = get_graph()
    initial_state: PipelineState = {
        "document_id": document_id,
        "raw_text": raw_text,
        "category_hint": None,
        "extraction": None,
        "qa_result": None,
        "status": None,
    }
    return graph.invoke(initial_state)
