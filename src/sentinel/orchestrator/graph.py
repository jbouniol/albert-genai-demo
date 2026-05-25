"""LangGraph orchestration — Sentinel multi-agent pipeline.

Graph topology:
    START → collector → analyzer → scorer → [conditional] → communicator → END
                                                  ↓ score ≤ HITL_TRIGGER
                                                 END

Nodes:
    collector    — loads & validates MetadataWindow from disk (no LLM)
    analyzer     — detects behavioral signals (gpt-4o, structured output)
    scorer       — aggregates signals into a 0-1 risk score (gpt-4o, structured output)
    communicator — drafts parent notification only if score > 0.65 (gpt-4o-mini)

State flows forward immutably: each node returns a dict with new/updated keys.

Phase 4: `callbacks` field carries token-streaming hooks (Communicator only).
Phase 5: `use_cache` field swaps in `CachedLLMClient` per agent.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from sentinel.agents.analyzer import Analyzer
from sentinel.agents.collector import Collector
from sentinel.agents.communicator import Communicator
from sentinel.agents.scorer import Scorer
from sentinel.config import HITL_TRIGGER, MODELS
from sentinel.data.models import AnalysisResult, MetadataWindow, ScoreResult
from sentinel.llm.cache import CachedLLMClient
from sentinel.llm.client import LLMClient

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """Shared state flowing through the Sentinel agent graph.

    `total=False` lets us pass partial dicts as initial state without filling
    in every key with `None`.
    """

    profile_id: str
    window: MetadataWindow | None
    analysis: AnalysisResult | None
    score_result: ScoreResult | None
    notification: str | None

    # Phase 4: optional streaming callbacks, keyed by agent name.
    # Only `on_communicator_delta` is currently consumed.
    callbacks: dict[str, Callable[[str], None]] | None

    # Phase 5: when True, swap in CachedLLMClient (disk replay, no API call).
    use_cache: bool


# ---------------------------------------------------------------------------
# Client factory (Phase 5)
# ---------------------------------------------------------------------------

def make_client(agent_name: str, state: AgentState) -> LLMClient | None:
    """Return a CachedLLMClient if state['use_cache'] else None (default LLM)."""
    if not state.get("use_cache"):
        return None
    profile_id = state.get("profile_id")
    if not profile_id:
        return None
    return CachedLLMClient(
        model=MODELS[agent_name],
        agent_name=agent_name,
        profile_id=profile_id,
    )


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def collector_node(state: AgentState) -> dict:
    """Load and validate the profile JSON — no LLM call."""
    agent = Collector()
    window = agent.run(state["profile_id"])
    return {"window": window}


def analyzer_node(state: AgentState) -> dict:
    """Detect behavioral risk signals from the MetadataWindow."""
    agent = Analyzer(client=make_client("analyzer", state))
    analysis = agent.run(state["window"])  # type: ignore[arg-type]
    return {"analysis": analysis}


def scorer_node(state: AgentState) -> dict:
    """Aggregate signals into a calibrated risk score."""
    agent = Scorer(client=make_client("scorer", state))
    score_result = agent.run(state["window"], state["analysis"])  # type: ignore[arg-type]
    return {"score_result": score_result}


def communicator_node(state: AgentState) -> dict:
    """Draft the parent notification (only reached when score > HITL_TRIGGER)."""
    callbacks = state.get("callbacks") or {}
    on_delta = callbacks.get("on_communicator_delta")
    agent = Communicator(client=make_client("communicator", state))
    notification = agent.run(
        state["window"],  # type: ignore[arg-type]
        state["score_result"],  # type: ignore[arg-type]
        on_text_delta=on_delta,
    )
    return {"notification": notification}


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

def _should_communicate(state: AgentState) -> str:
    """Route to communicator only when the risk score exceeds the HITL threshold."""
    score_result = state.get("score_result")
    if score_result is not None and score_result.score > HITL_TRIGGER:
        return "communicate"
    return "done"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Assemble and compile the Sentinel LangGraph."""
    builder = StateGraph(AgentState)

    builder.add_node("collector", collector_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("scorer", scorer_node)
    builder.add_node("communicator", communicator_node)

    builder.add_edge(START, "collector")
    builder.add_edge("collector", "analyzer")
    builder.add_edge("analyzer", "scorer")
    builder.add_conditional_edges(
        "scorer",
        _should_communicate,
        {"communicate": "communicator", "done": END},
    )
    builder.add_edge("communicator", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# Optional: save graph PNG (uses mermaid.ink, non-blocking)
# ---------------------------------------------------------------------------

def save_graph_png(output_path: str | Path = "graph.png") -> bool:
    """Save a Mermaid PNG of the graph. Returns True on success."""
    try:
        graph = build_graph()
        png_bytes = graph.get_graph().draw_mermaid_png()
        Path(output_path).write_bytes(png_bytes)
        return True
    except Exception:
        return False
