"""Agent node implementations.

Each function takes the full `ResearchState` and returns a *partial* state dict
that LangGraph merges into the global state. Keeping every node side-effect-free
(apart from network calls) makes them trivially unit-testable.
"""
from __future__ import annotations

import logging
from typing import Any

from .llm import chat, chat_json
from .search import dedupe_papers, search_papers
from .state import PaperRecord, PaperSummary, ResearchState

log = logging.getLogger(__name__)

SUB_QUERY_COUNT = 4
PAPERS_PER_QUERY = 4


# ---------------------------------------------------------------------------
# 1. Query Planner
# ---------------------------------------------------------------------------
def query_planner_node(state: ResearchState) -> dict[str, Any]:
    topic = state["original_query"]
    feedback = state.get("feedback")

    # Guardrail: Policy and off-topic check
    clean_topic = topic.strip().lower()
    greetings = {"hello", "hi", "hey"}
    words = set(clean_topic.split())
    phrases = ["ignore previous instructions", "system prompt", "write a joke", "tell me a story", "how are you", "who are you"]
    is_off_topic = (
        not words.isdisjoint(greetings) or 
        any(p in clean_topic for p in phrases) or 
        len(clean_topic) < 10
    )
    
    if is_off_topic:
        log.warning("Guardrail refusal: Input query '%s' violates topic policy", topic)
        return {
            "stage": "error",
            "error": "Query Refusal: The provided input topic does not meet academic research policy requirements or is off-topic."
        }

    system = (
        "You are a senior research strategist. Decompose a research topic into "
        f"{SUB_QUERY_COUNT} distinct, search-optimised sub-queries suitable for "
        "ArXiv. Each sub-query should target a different facet (e.g. methods, "
        "applications, evaluation, limitations, recent advances). Return strict "
        'JSON of the form {"sub_queries": ["...", "..."]} with no commentary.'
    )
    user = f"Research topic: {topic}"
    if feedback:
        user += (
            "\n\nThe previous outline was rejected with this human feedback:\n"
            f"{feedback}\n\nReformulate the sub-queries to address it."
        )

    try:
        payload = chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
        )
        sub_queries = [s.strip() for s in payload.get("sub_queries", []) if s and s.strip()]
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("Planner failed")
        return {"stage": "error", "error": f"Planner failed: {exc}"}

    if not sub_queries:
        return {"stage": "error", "error": "Planner returned no sub-queries."}

    return {"stage": "planning", "sub_queries": sub_queries[:SUB_QUERY_COUNT]}
