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


# ---------------------------------------------------------------------------
# 2. Search Agent
# ---------------------------------------------------------------------------
def search_node(state: ResearchState) -> dict[str, Any]:
    sub_queries = state.get("sub_queries", [])
    bag: list[PaperRecord] = []
    for q in sub_queries:
        bag.extend(search_papers(q, max_results=PAPERS_PER_QUERY))
    deduped = dedupe_papers(bag)
    if not deduped:
        return {
            "stage": "error",
            "error": "Search returned 0 papers across all sub-queries. "
                     "Check network access to export.arxiv.org.",
        }
    return {"stage": "searching", "downloaded_papers": deduped}


# ---------------------------------------------------------------------------
# 3. Reading Agent
# ---------------------------------------------------------------------------
_READING_SYSTEM = (
    "You are a meticulous research analyst. Given a paper's title and abstract, "
    "extract its structured essentials. Return strict JSON with this schema:\n"
    "{\n"
    '  "core_claims": ["..."],   // 2-4 bullet claims\n'
    '  "methodology": "...",      // 1-3 sentence description\n'
    '  "limitations": ["..."],   // 1-3 explicit or inferred limitations\n'
    '  "relevance": "..."         // 1-sentence relevance to the parent topic\n'
    "}\n"
    "Do not invent details that are not implied by the abstract."
)


def reading_node(state: ResearchState) -> dict[str, Any]:
    topic = state["original_query"]
    papers = state.get("downloaded_papers", [])
    summaries: list[PaperSummary] = []
    for paper in papers:
        user_msg = (
            f"Parent research topic: {topic}\n\n"
            f"Title: {paper.get('title')}\n"
            f"Authors: {', '.join(paper.get('authors', []))}\n"
            f"Abstract: {paper.get('abstract')}\n"
        )
        try:
            data = chat_json(
                [
                    {"role": "system", "content": _READING_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
            )
        except Exception as exc:
            log.warning("Reading failed for %s: %s", paper.get("paper_id"), exc)
            data = {
                "core_claims": [],
                "methodology": "",
                "limitations": [],
                "relevance": "(summary unavailable)",
            }
        summaries.append(
            PaperSummary(
                paper_id=paper.get("paper_id", ""),
                title=paper.get("title", ""),
                url=paper.get("url", ""),
                core_claims=list(data.get("core_claims") or []),
                methodology=str(data.get("methodology") or ""),
                limitations=list(data.get("limitations") or []),
                relevance=str(data.get("relevance") or ""),
            )
        )
    return {"stage": "reading", "paper_summaries": summaries}
