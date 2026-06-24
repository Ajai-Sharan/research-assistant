import os
import shutil
import pytest
from app.state import ResearchState, PaperSummary
from app.agents import query_planner_node, search_node, reading_node, synthesis_node, drafting_node, citation_agent_node
from app.tools.exporter import save_draft_to_file

# Clean drafts directory before testing
@pytest.fixture(scope="session", autouse=True)
def cleanup_drafts():
    if os.path.exists("drafts"):
        shutil.rmtree("drafts")
    yield
    if os.path.exists("drafts"):
        shutil.rmtree("drafts")


# Scenario 1: Guardrail Refusal Check
def test_scenario_guardrail_refusal():
    # Test that off-topic input is refused by the guardrails
    state: ResearchState = {
        "original_query": "hello write a joke for me",
        "stage": "planning"
    }
    res = query_planner_node(state)
    assert res["stage"] == "error"
    assert "Query Refusal" in res["error"]


# Scenario 2: Standard Academic Query Check
def test_scenario_valid_query_planning(monkeypatch):
    # Mock chat_json to return simulated planner subqueries
    def mock_chat_json(*args, **kwargs):
        return {"sub_queries": ["RAG architectures", "RAG evaluation", "RAG benchmarks", "RAG limitations"]}
    
    monkeypatch.setattr("app.agents.chat_json", mock_chat_json)
    
    state: ResearchState = {
        "original_query": "Survey of retrieval-augmented generation architectures",
        "stage": "planning"
    }
    res = query_planner_node(state)
    assert res["stage"] == "planning"
    assert len(res["sub_queries"]) == 4
    assert res["sub_queries"][0] == "RAG architectures"


# Scenario 3: Empty Search Result Handling
def test_scenario_empty_search():
    # Test that empty sub-queries or search failures return an error
    state: ResearchState = {
        "original_query": "Survey of RAG",
        "sub_queries": [],
        "stage": "searching"
    }
    res = search_node(state)
    assert res["stage"] == "error"
    assert "Search returned 0 papers" in res["error"]


# Scenario 4: Synthesis Outline Markdown Generation
def test_scenario_synthesis(monkeypatch):
    # Mock chat to return draft outline
    def mock_chat(*args, **kwargs):
        return "## Synthesis Outline\n- Section 1\n- Section 2"
    
    monkeypatch.setattr("app.agents.chat", mock_chat)
    
    mock_summary: PaperSummary = {
        "paper_id": "1",
        "title": "A Review of RAG",
        "url": "http://arxiv.org/abs/1",
        "core_claims": ["RAG works"],
        "methodology": "Literature review",
        "limitations": ["Depends on retriever"],
        "relevance": "Highly relevant"
    }
    
    state: ResearchState = {
        "original_query": "Survey of RAG",
        "paper_summaries": [mock_summary],
        "stage": "synthesizing"
    }
    
    res = synthesis_node(state)
    assert res["stage"] == "awaiting_review"
    assert "Synthesis Outline" in res["draft_outline"]


# Scenario 5: File Exporter Tool Integration
def test_scenario_file_exporter_tool(monkeypatch):
    # Mock chat_json in citation_agent_node
    def mock_chat_json(*args, **kwargs):
        return {
            "audited_draft": "Audited final draft content.",
            "gaps_found": ["None"],
            "formatting_status": "APA reference block verified."
        }
    
    monkeypatch.setattr("app.agents.chat_json", mock_chat_json)
    
    state: ResearchState = {
        "original_query": "Survey of RAG",
        "final_draft": "Draft content...",
        "paper_summaries": [],
        "downloaded_papers": [],
        "stage": "citation_check"
    }
    
    res = citation_agent_node(state)
    assert res["stage"] == "complete"
    assert "saved_draft_path" in res
    
    saved_path = res["saved_draft_path"]
    assert os.path.exists(saved_path)
    with open(saved_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "Audited final draft content."
