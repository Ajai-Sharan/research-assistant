"""FastAPI entry point.

Endpoints:
  POST /api/start-research        -- kick off a new graph run
  GET  /api/status/{job_id}       -- poll current state
  POST /api/submit-feedback/{id}  -- approve outline or send revision feedback

The graph runs in a background thread (FastAPI's BackgroundTasks) so the
HTTP request returns immediately and the Streamlit UI can poll for progress.
"""
from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .graph import GRAPH, is_awaiting_review, snapshot, thread_config
from .state import (
    FeedbackRequest,
    ResearchState,
    StartRequest,
    StartResponse,
    StatusResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("research_assistant")

import os
if os.environ.get("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = os.environ.get("LANGCHAIN_PROJECT", "research-assistant")

app = FastAPI(title="AI Research Paper Assistant", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track in-flight background threads so we can avoid double-resuming a job.
_job_locks: dict[str, threading.Lock] = {}


def _lock_for(job_id: str) -> threading.Lock:
    return _job_locks.setdefault(job_id, threading.Lock())


# ---------------------------------------------------------------------------
# Background runners
# ---------------------------------------------------------------------------
def _run_initial(job_id: str, topic: str) -> None:
    """Stream the graph until the first interrupt or completion."""
    lock = _lock_for(job_id)
    with lock:
        cfg = thread_config(job_id)
        initial: ResearchState = {
            "original_query": topic,
            "stage": "queued",
            "feedback": None,
            "error": None,
        }
        try:
            for _ in GRAPH.stream(initial, cfg, stream_mode="values"):
                # We do not need the per-step payload here; the checkpointer
                # has already persisted it and the /status route reads from
                # the checkpointer.
                pass
        except Exception as exc:  # pragma: no cover
            log.exception("Initial graph run failed for %s", job_id)
            GRAPH.update_state(cfg, {"stage": "error", "error": str(exc)})


def _resume(job_id: str, *, feedback: str | None, revise: bool) -> None:
    lock = _lock_for(job_id)
    with lock:
        cfg = thread_config(job_id)
        if revise:
            # Re-route back to the planner with the human feedback baked in.
            GRAPH.update_state(
                cfg,
                {"stage": "planning", "feedback": feedback or ""},
                as_node="human_review",  # treat as resumption from the review node
            )
            # Replay from the planner explicitly by invoking with None values.
            try:
                # We invoke the planner -> synthesizer chain again. The
                # checkpointer keeps history; passing `None` tells LangGraph
                # to continue from the last checkpoint.
                for _ in GRAPH.stream(None, cfg, stream_mode="values"):
                    pass
            except Exception as exc:  # pragma: no cover
                log.exception("Revision run failed for %s", job_id)
                GRAPH.update_state(cfg, {"stage": "error", "error": str(exc)})
            return

        # Approval path: simply continue past the interrupt.
        try:
            for _ in GRAPH.stream(None, cfg, stream_mode="values"):
                pass
        except Exception as exc:  # pragma: no cover
            log.exception("Resume failed for %s", job_id)
            GRAPH.update_state(cfg, {"stage": "error", "error": str(exc)})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _state_to_response(job_id: str, state: ResearchState) -> StatusResponse:
    return StatusResponse(
        job_id=job_id,
        stage=state.get("stage", "unknown"),
        awaiting_review=is_awaiting_review(job_id),
        error=state.get("error"),
        sub_queries=list(state.get("sub_queries") or []),
        downloaded_papers=[dict(p) for p in (state.get("downloaded_papers") or [])],
        paper_summaries=[dict(s) for s in (state.get("paper_summaries") or [])],
        draft_outline=state.get("draft_outline"),
        final_draft=state.get("final_draft"),
        citation_report=state.get("citation_report"),
        saved_draft_path=state.get("saved_draft_path"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/start-research", response_model=StartResponse)
def start_research(req: StartRequest, background: BackgroundTasks) -> StartResponse:
    job_id = uuid.uuid4().hex
    log.info("Starting job %s for topic=%r", job_id, req.topic)
    _lock_for(job_id)  # Register the job so the status endpoint knows it's active
    background.add_task(_run_initial, job_id, req.topic)
    return StartResponse(job_id=job_id, status="queued")


@app.get("/api/status/{job_id}", response_model=StatusResponse)
def status(job_id: str) -> StatusResponse:
    state = snapshot(job_id)
    if not state:
        if job_id in _job_locks:
            return StatusResponse(
                job_id=job_id,
                stage="queued",
                awaiting_review=False,
                sub_queries=[],
                downloaded_papers=[],
                paper_summaries=[],
            )
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return _state_to_response(job_id, state)


@app.post("/api/submit-feedback/{job_id}", response_model=StatusResponse)
def submit_feedback(
    job_id: str, req: FeedbackRequest, background: BackgroundTasks
) -> StatusResponse:
    state = snapshot(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    if not is_awaiting_review(job_id):
        raise HTTPException(
            status_code=409,
            detail=f"Job is in stage '{state.get('stage')}', not awaiting review.",
        )

    if req.decision == "revise" and not (req.feedback and req.feedback.strip()):
        raise HTTPException(
            status_code=400, detail="Revision requested but no feedback text provided."
        )

    background.add_task(
        _resume,
        job_id,
        feedback=req.feedback,
        revise=(req.decision == "revise"),
    )
    # Reflect immediate stage change in the response so the UI doesn't flash
    # the old "awaiting_review" status.
    return StatusResponse(
        job_id=job_id,
        stage="drafting" if req.decision == "approve" else "planning",
        awaiting_review=False,
        sub_queries=list(state.get("sub_queries") or []),
        downloaded_papers=[dict(p) for p in (state.get("downloaded_papers") or [])],
        paper_summaries=[dict(s) for s in (state.get("paper_summaries") or [])],
        draft_outline=state.get("draft_outline"),
        final_draft=state.get("final_draft"),
        citation_report=state.get("citation_report"),
    )


# Serve built React SPA if the distribution folder exists
import os
from fastapi.staticfiles import StaticFiles

dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
