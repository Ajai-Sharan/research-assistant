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


# ---------------------------------------------------------------------------
# 4. Synthesis Agent
# ---------------------------------------------------------------------------
_SYNTHESIS_SYSTEM = (
    "You are a senior literature-review editor. Using the structured summaries "
    "below, produce a 'Literature Outline' in Markdown that:\n"
    "1. Groups related findings into thematic sections.\n"
    "2. Explicitly flags contradictions between papers (use '> Contradiction:' callouts).\n"
    "3. Uses inline citations of the form [P#] where # is the 1-based index of "
    "   the paper as supplied.\n"
    "4. Ends with a 'Suggested Draft Structure' section listing the chapters/"
    "   sections the final paper should contain.\n"
    "Do not output the final paper itself -- only the outline."
)


def _format_summaries_for_prompt(summaries: list[PaperSummary]) -> str:
    lines: list[str] = []
    for idx, s in enumerate(summaries, start=1):
        lines.append(f"[P{idx}] {s.get('title')}  ({s.get('url')})")
        if s.get("core_claims"):
            lines.append("  Claims: " + "; ".join(s["core_claims"]))
        if s.get("methodology"):
            lines.append(f"  Methodology: {s['methodology']}")
        if s.get("limitations"):
            lines.append("  Limitations: " + "; ".join(s["limitations"]))
        if s.get("relevance"):
            lines.append(f"  Relevance: {s['relevance']}")
        lines.append("")
    return "\n".join(lines)


def synthesis_node(state: ResearchState) -> dict[str, Any]:
    summaries = state.get("paper_summaries", [])
    topic = state["original_query"]
    feedback = state.get("feedback")

    user_parts = [f"Research topic: {topic}", "", "Paper summaries:", _format_summaries_for_prompt(summaries)]
    if feedback:
        user_parts.extend(["", "Human reviewer feedback to incorporate:", feedback])

    try:
        outline = chat(
            [
                {"role": "system", "content": _SYNTHESIS_SYSTEM},
                {"role": "user", "content": "\n".join(user_parts)},
            ],
            temperature=0.4,
        )
    except Exception as exc:
        log.exception("Synthesis failed")
        return {"stage": "error", "error": f"Synthesis failed: {exc}"}

    return {"stage": "awaiting_review", "draft_outline": outline.strip()}


# ---------------------------------------------------------------------------
# 5. Human Review Node -- a pass-through; the *interrupt* is what pauses us.
# ---------------------------------------------------------------------------
def human_review_node(state: ResearchState) -> dict[str, Any]:
    # When the graph is resumed (post-approval) this runs and clears feedback
    # so the drafting agent sees a clean slate.
    return {"stage": "drafting", "feedback": None}


# ---------------------------------------------------------------------------
# 6. Citation & Drafting Agent
# ---------------------------------------------------------------------------
_DRAFTING_SYSTEM = (
    "You are a scholarly writer. Produce a complete research document in "
    "Markdown that follows the approved outline. Every non-trivial claim MUST "
    "be supported by an inline citation in the form [P#]. Conclude with a "
    "'References' section listing each cited paper as:\n"
    "[P#] Authors. *Title*. URL\n"
    "Do not invent papers; only cite from the provided list."
)


def _format_references_block(summaries: list[PaperSummary], papers: list[PaperRecord]) -> str:
    by_id = {p.get("paper_id"): p for p in papers}
    lines = []
    for idx, s in enumerate(summaries, start=1):
        paper = by_id.get(s.get("paper_id"), {})
        authors = ", ".join(paper.get("authors", [])) or "Unknown authors"
        lines.append(f"[P{idx}] {authors}. *{s.get('title')}*. {s.get('url')}")
    return "\n".join(lines)


def drafting_node(state: ResearchState) -> dict[str, Any]:
    topic = state["original_query"]
    summaries = state.get("paper_summaries", [])
    outline = state.get("draft_outline", "")

    user = (
        f"Research topic: {topic}\n\n"
        f"Approved outline:\n{outline}\n\n"
        f"Paper summaries (cite as [P#] using these indices):\n"
        f"{_format_summaries_for_prompt(summaries)}"
    )

    try:
        draft = chat(
            [
                {"role": "system", "content": _DRAFTING_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.5,
            max_tokens=3000,
        )
    except Exception as exc:
        log.exception("Drafting failed")
        return {"stage": "error", "error": f"Drafting failed: {exc}"}

    # Guarantee the references block exists even if the model omitted it.
    refs = _format_references_block(summaries, state.get("downloaded_papers", []))
    if "References" not in draft:
        draft = f"{draft.strip()}\n\n## References\n\n{refs}\n"

    return {"stage": "complete", "final_draft": draft.strip()}
