"""Graph state schema and API-layer Pydantic models.

The `ResearchState` TypedDict is the single source of truth for what flows
through the LangGraph. API models live alongside it because they are thin
projections of the same data.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# LangGraph state contract
# ---------------------------------------------------------------------------
class PaperRecord(TypedDict, total=False):
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    published: str
    source_query: str


class PaperSummary(TypedDict, total=False):
    paper_id: str
    title: str
    url: str
    core_claims: list[str]
    methodology: str
    limitations: list[str]
    relevance: str


class ResearchState(TypedDict, total=False):
    # Inputs
    original_query: str
    feedback: str | None  # optional human revision feedback

    # Stage outputs
    sub_queries: list[str]
    downloaded_papers: list[PaperRecord]
    paper_summaries: list[PaperSummary]
    draft_outline: str
    final_draft: str
    citation_report: str | None
    saved_draft_path: str

    # Observability
    stage: str          # which agent is currently / was last active
    error: str | None   # populated if a node raises


STAGES: tuple[str, ...] = (
    "queued",
    "planning",
    "searching",
    "reading",
    "synthesizing",
    "awaiting_review",
    "drafting",
    "citation_check",
    "complete",
    "error",
)


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------
class StartRequest(BaseModel):
    topic: str = Field(..., min_length=4, description="Research topic / assignment brief.")


class StartResponse(BaseModel):
    job_id: str
    status: str


class FeedbackRequest(BaseModel):
    decision: Literal["approve", "revise"]
    feedback: str | None = None


class StatusResponse(BaseModel):
    job_id: str
    stage: str
    awaiting_review: bool
    error: str | None = None
    sub_queries: list[str] = []
    downloaded_papers: list[dict[str, Any]] = []
    paper_summaries: list[dict[str, Any]] = []
    draft_outline: str | None = None
    final_draft: str | None = None
    citation_report: str | None = None
    saved_draft_path: str | None = None
