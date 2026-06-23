"""LangGraph wiring.

We expose a single `build_graph()` factory plus tiny helpers that the FastAPI
layer uses to (a) start a fresh run and (b) resume after the human-review
interrupt. The MemorySaver checkpointer is intentionally process-local --
swap it for SQLite/Postgres when you need multi-replica deployments.
"""
from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .agents import (
    drafting_node,
    human_review_node,
    query_planner_node,
    reading_node,
    search_node,
    synthesis_node,
    citation_agent_node,
)
from .state import ResearchState


def _route_after_node(state: ResearchState) -> str:
    """Short-circuit to END if any upstream node recorded an error."""
    return "error" if state.get("error") else "ok"


def build_graph() -> Any:
    g = StateGraph(ResearchState)

    g.add_node("planner", query_planner_node)
    g.add_node("search", search_node)
    g.add_node("reader", reading_node)
    g.add_node("synthesizer", synthesis_node)
    g.add_node("human_review", human_review_node)
    g.add_node("drafter", drafting_node)
    g.add_node("citation_agent", citation_agent_node)

    g.set_entry_point("planner")

    # Linear happy-path with error short-circuiting after each LLM/IO node.
    for src, dst in (
        ("planner", "search"),
        ("search", "reader"),
        ("reader", "synthesizer"),
    ):
        g.add_conditional_edges(
            src,
            _route_after_node,
            {"ok": dst, "error": END},
        )

    # Synthesizer -> human_review (with an explicit interrupt_before below)
    g.add_conditional_edges(
        "synthesizer",
        _route_after_node,
        {"ok": "human_review", "error": END},
    )
    g.add_edge("human_review", "drafter")
    
    # Drafter -> citation_agent with error checking
    g.add_conditional_edges(
        "drafter",
        _route_after_node,
        {"ok": "citation_agent", "error": END},
    )
    g.add_edge("citation_agent", END)

    checkpointer = MemorySaver()
    return g.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )


# Module-level singleton; FastAPI imports this directly.
GRAPH = build_graph()


def thread_config(job_id: str) -> dict[str, Any]:
    """LangGraph addresses checkpointed conversations via `thread_id`."""
    return {"configurable": {"thread_id": job_id}}


def snapshot(job_id: str) -> ResearchState:
    """Return the latest persisted state for a given job."""
    state = GRAPH.get_state(thread_config(job_id))
    # state.values is the merged ResearchState dict
    return state.values if state else {}


def is_awaiting_review(job_id: str) -> bool:
    state = GRAPH.get_state(thread_config(job_id))
    if not state:
        return False
    # `next` is the tuple of nodes pending execution. If the human_review node
    # is up next, it means the interrupt_before paused us right before it.
    return "human_review" in (state.next or ())
