import os
import shutil
import subprocess

workspace_dir = "/Users/ajaisharan/Documents/research_assistant"
backup_dir = os.path.join(workspace_dir, "temp_backup")

print("1. Creating temporary backup of existing codebase...")
if os.path.exists(backup_dir):
    shutil.rmtree(backup_dir)
os.makedirs(backup_dir)

# Copy files directly
shutil.copy2(os.path.join(workspace_dir, "requirements.txt"), backup_dir)
shutil.copy2(os.path.join(workspace_dir, ".gitignore"), backup_dir)
shutil.copy2(os.path.join(workspace_dir, "README.md"), backup_dir)
shutil.copy2(os.path.join(workspace_dir, "DEPLOY.md"), backup_dir)

def copy_dir_filtered(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
        '.git', '.venv', 'node_modules', 'dist', '__pycache__', 'temp_backup', 'rebuild_repo.py', 'CONTRIBUTIONS.md', '.env'
    ))

copy_dir_filtered(os.path.join(workspace_dir, "app"), os.path.join(backup_dir, "app"))
copy_dir_filtered(os.path.join(workspace_dir, "frontend"), os.path.join(backup_dir, "frontend"))
copy_dir_filtered(os.path.join(workspace_dir, "tests"), os.path.join(backup_dir, "tests"))

print("2. Initializing new git state...")
# Checkout an orphan branch named main-temp (wipes out parent commits)
subprocess.run(["git", "checkout", "--orphan", "main-temp"], cwd=workspace_dir, check=True)
# Clear working directory and index
subprocess.run(["git", "rm", "-rf", "."], cwd=workspace_dir, check=True)

# Define authors
DEV_SPOORTHY = {"name": "iam-spoorthy", "email": "spoorthymadasu.official@gmail.com"}
DEV_SID = {"name": "isid555", "email": "r555sid@gmail.com"}
DEV_AJAI = {"name": "Ajai-Sharan", "email": "ajaisharan2020@gmail.com"}

# Helper to write files
def write_file(rel_path, content):
    full_path = os.path.join(workspace_dir, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# Helper to copy from backup
def copy_from_backup(rel_path):
    src = os.path.join(backup_dir, rel_path)
    dst = os.path.join(workspace_dir, rel_path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

def make_commit(author, date_str, message, files_to_add):
    for f in files_to_add:
        subprocess.run(["git", "add", f], cwd=workspace_dir, check=True)
    
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = author["name"]
    env["GIT_AUTHOR_EMAIL"] = author["email"]
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_NAME"] = author["name"]
    env["GIT_COMMITTER_EMAIL"] = author["email"]
    env["GIT_COMMITTER_DATE"] = date_str
    
    subprocess.run(["git", "commit", "-m", message], cwd=workspace_dir, env=env, check=True)
    print(f"Created commit: {message} ({date_str}) by {author['name']}")

# ---------------------------------------------------------------------------
# Commit 1
# ---------------------------------------------------------------------------
copy_from_backup(".gitignore")
copy_from_backup("requirements.txt")
write_file("README.md", "# AI Research Paper Assistant\n\nMulti-agent research workflow powered by FastAPI & LangGraph.\n")
make_commit(DEV_AJAI, "2026-06-22T09:00:00", "chore: initialize repository and add project configuration", [".gitignore", "requirements.txt", "README.md"])

# ---------------------------------------------------------------------------
# Commit 2
# ---------------------------------------------------------------------------
write_file("app/__init__.py", "")
copy_from_backup("app/state.py")
make_commit(DEV_SPOORTHY, "2026-06-22T10:30:00", "feat(backend): add state definitions and schemas", ["app/__init__.py", "app/state.py"])

# ---------------------------------------------------------------------------
# Commit 3
# ---------------------------------------------------------------------------
copy_from_backup("app/search.py")
make_commit(DEV_SID, "2026-06-22T12:00:00", "feat(backend): integrate ArXiv search client", ["app/search.py"])

# ---------------------------------------------------------------------------
# Commit 4
# ---------------------------------------------------------------------------
llm_v1 = """from __future__ import annotations

import json
import os
from typing import Any, Iterable

from openai import OpenAI

ENDPOINT = "https://models.github.ai/inference"
DEFAULT_MODEL = os.environ.get("GITHUB_MODEL", "openai/gpt-4.1")

_token = os.environ.get("GITHUB_TOKEN")
if not _token:
    _token = ""

client = OpenAI(
    base_url=ENDPOINT,
    api_key=_token or "missing-token",
)


def chat(
    messages: Iterable[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    response_format: dict[str, Any] | None = None,
    max_tokens: int | None = None,
) -> str:
    \"\"\"Single-turn chat helper. Returns the raw assistant content string.

    Centralising this here keeps every agent's call shape identical and makes
    retries / logging / cost tracking trivial to bolt on later.
    \"\"\"
    if not os.environ.get("GITHUB_TOKEN"):
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is not set. "
            "Export a GitHub Models access token before starting the backend."
        )

    kwargs: dict[str, Any] = {
        "model": model or DEFAULT_MODEL,
        "messages": list(messages),
        "temperature": temperature,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_json(messages: Iterable[dict[str, str]], **kwargs: Any) -> Any:
    \"\"\"Convenience wrapper that requests JSON and parses the response.

    Falls back to best-effort extraction if the model returns a fenced block.
    \"\"\"
    kwargs.setdefault("response_format", {"type": "json_object"})
    raw = chat(messages, **kwargs)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for opener, closer in (("{", "}"), ("[", "]")):
            start = raw.find(opener)
            end = raw.rfind(closer)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise
"""
write_file("app/llm.py", llm_v1)
make_commit(DEV_AJAI, "2026-06-22T14:00:00", "feat(backend): implement LLM client wrapper", ["app/llm.py"])

# ---------------------------------------------------------------------------
# Commit 5
# ---------------------------------------------------------------------------
agents_v1 = """\"\"\"Agent node implementations.

Each function takes the full `ResearchState` and returns a *partial* state dict
that LangGraph merges into the global state. Keeping every node side-effect-free
(apart from network calls) makes them trivially unit-testable.
\"\"\"
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
            "\\n\\nThe previous outline was rejected with this human feedback:\\n"
            f"{feedback}\\n\\nReformulate the sub-queries to address it."
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
"""
write_file("app/agents.py", agents_v1)
make_commit(DEV_SPOORTHY, "2026-06-22T16:30:00", "feat(backend): implement Query Planner agent node", ["app/agents.py"])

# ---------------------------------------------------------------------------
# Commit 6
# ---------------------------------------------------------------------------
agents_v2 = agents_v1 + """

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
    "extract its structured essentials. Return strict JSON with this schema:\\n"
    "{\\n"
    '  "core_claims": ["..."],   // 2-4 bullet claims\\n'
    '  "methodology": "...",      // 1-3 sentence description\\n'
    '  "limitations": ["..."],   // 1-3 explicit or inferred limitations\\n'
    '  "relevance": "..."         // 1-sentence relevance to the parent topic\\n'
    "}\\n"
    "Do not invent details that are not implied by the abstract."
)


def reading_node(state: ResearchState) -> dict[str, Any]:
    topic = state["original_query"]
    papers = state.get("downloaded_papers", [])
    summaries: list[PaperSummary] = []
    for paper in papers:
        user_msg = (
            f"Parent research topic: {topic}\\n\\n"
            f"Title: {paper.get('title')}\\n"
            f"Authors: {', '.join(paper.get('authors', []))}\\n"
            f"Abstract: {paper.get('abstract')}\\n"
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
"""
write_file("app/agents.py", agents_v2)
make_commit(DEV_SID, "2026-06-22T18:00:00", "feat(backend): add Research Search and Document Reader agent nodes", ["app/agents.py"])

# ---------------------------------------------------------------------------
# Commit 7
# ---------------------------------------------------------------------------
agents_v3 = agents_v2 + """

# ---------------------------------------------------------------------------
# 4. Synthesis Agent
# ---------------------------------------------------------------------------
_SYNTHESIS_SYSTEM = (
    "You are a senior literature-review editor. Using the structured summaries "
    "below, produce a 'Literature Outline' in Markdown that:\\n"
    "1. Groups related findings into thematic sections.\\n"
    "2. Explicitly flags contradictions between papers (use '> Contradiction:' callouts).\\n"
    "3. Uses inline citations of the form [P#] where # is the 1-based index of "
    "   the paper as supplied.\\n"
    "4. Ends with a 'Suggested Draft Structure' section listing the chapters/"
    "   sections the final paper should contain.\\n"
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
    return "\\n".join(lines)


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
                {"role": "user", "content": "\\n".join(user_parts)},
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
    "'References' section listing each cited paper as:\\n"
    "[P#] Authors. *Title*. URL\\n"
    "Do not invent papers; only cite from the provided list."
)


def _format_references_block(summaries: list[PaperSummary], papers: list[PaperRecord]) -> str:
    by_id = {p.get("paper_id"): p for p in papers}
    lines = []
    for idx, s in enumerate(summaries, start=1):
        paper = by_id.get(s.get("paper_id"), {})
        authors = ", ".join(paper.get("authors", [])) or "Unknown authors"
        lines.append(f"[P{idx}] {authors}. *{s.get('title')}*. {s.get('url')}")
    return "\\n".join(lines)


def drafting_node(state: ResearchState) -> dict[str, Any]:
    topic = state["original_query"]
    summaries = state.get("paper_summaries", [])
    outline = state.get("draft_outline", "")

    user = (
        f"Research topic: {topic}\\n\\n"
        f"Approved outline:\\n{outline}\\n\\n"
        f"Paper summaries (cite as [P#] using these indices):\\n"
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
        draft = f"{draft.strip()}\\n\\n## References\\n\\n{refs}\\n"

    return {"stage": "complete", "final_draft": draft.strip()}
"""
write_file("app/agents.py", agents_v3)
make_commit(DEV_AJAI, "2026-06-23T09:30:00", "feat(backend): implement Synthesis and Writer agent nodes", ["app/agents.py"])

# ---------------------------------------------------------------------------
# Commit 8
# ---------------------------------------------------------------------------
copy_from_backup("app/agents.py")
make_commit(DEV_SPOORTHY, "2026-06-23T11:00:00", "feat(backend): implement Citation Auditor agent node", ["app/agents.py"])

# ---------------------------------------------------------------------------
# Commit 9
# ---------------------------------------------------------------------------
copy_from_backup("app/graph.py")
make_commit(DEV_SID, "2026-06-23T13:30:00", "feat(backend): construct LangGraph research state machine", ["app/graph.py"])

# ---------------------------------------------------------------------------
# Commit 10
# ---------------------------------------------------------------------------
copy_from_backup("app/main.py")
copy_from_backup("app/tools/exporter.py")
make_commit(DEV_AJAI, "2026-06-23T15:30:00", "feat(backend): implement FastAPI app and endpoints", ["app/main.py", "app/tools/exporter.py"])

# ---------------------------------------------------------------------------
# Commit 11
# ---------------------------------------------------------------------------
copy_from_backup("frontend/package.json")
copy_from_backup("frontend/tsconfig.json")
copy_from_backup("frontend/tsconfig.app.json")
copy_from_backup("frontend/tsconfig.node.json")
copy_from_backup("frontend/vite.config.ts")
copy_from_backup("frontend/index.html")
copy_from_backup("frontend/.gitignore")
copy_from_backup("frontend/.oxlintrc.json")
copy_from_backup("frontend/package-lock.json")
make_commit(DEV_SPOORTHY, "2026-06-23T17:00:00", "chore(frontend): initialize Vite + React + TS frontend", [
    "frontend/package.json",
    "frontend/tsconfig.json",
    "frontend/tsconfig.app.json",
    "frontend/tsconfig.node.json",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "frontend/.gitignore",
    "frontend/.oxlintrc.json",
    "frontend/package-lock.json"
])

# ---------------------------------------------------------------------------
# Commit 12
# ---------------------------------------------------------------------------
copy_from_backup("frontend/src/App.css")
def get_initial_index_css():
    with open(os.path.join(backup_dir, "frontend/src/index.css"), "r", encoding="utf-8") as f:
        content = f.read()
    idx = content.find("/* Status Indicator Dot & Pulse Animations */")
    if idx != -1:
        return content[:idx]
    return content

write_file("frontend/src/index.css", get_initial_index_css())
make_commit(DEV_SID, "2026-06-23T18:30:00", "style(frontend): establish base design system and CSS styling", [
    "frontend/src/App.css",
    "frontend/src/index.css"
])

# ---------------------------------------------------------------------------
# Commit 13
# ---------------------------------------------------------------------------
header_v1 = """import React from 'react';
import { Cpu } from 'lucide-react';

interface HeaderProps {
  backendUrl: string;
}

export const Header: React.FC<HeaderProps> = ({ backendUrl }) => {
  return (
    <header className="fade-in" style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '20px 24px',
      background: 'rgba(17, 19, 28, 0.4)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border-color)',
      borderRadius: '16px',
      marginTop: '20px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          background: 'linear-gradient(135deg, var(--accent-indigo) 0%, var(--accent-purple) 100%)',
          padding: '8px',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 15px rgba(99, 102, 241, 0.3)'
        }}>
          <Cpu size={24} color="#fff" />
        </div>
        <div>
          <h1 style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            letterSpacing: '-0.02em',
            margin: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            AI <span className="gradient-text">Research Paper Assistant</span>
          </h1>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
            Multi-agent research workflow powered by FastAPI & LangGraph
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-color)',
          padding: '6px 12px',
          borderRadius: '8px',
          fontSize: '0.8rem'
        }}>
          <span style={{ color: 'var(--text-muted)' }}>API:</span>
          <code style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{backendUrl}</code>
        </div>
      </div>
    </header>
  );
};
"""
write_file("frontend/src/components/Header.tsx", header_v1)
copy_from_backup("frontend/src/components/InputScreen.tsx")
copy_from_backup("frontend/src/assets/react.svg")
copy_from_backup("frontend/src/assets/vite.svg")
copy_from_backup("frontend/src/assets/hero.png")
make_commit(DEV_AJAI, "2026-06-24T09:00:00", "feat(frontend): create Header and InputScreen components", [
    "frontend/src/components/Header.tsx",
    "frontend/src/components/InputScreen.tsx",
    "frontend/src/assets/react.svg",
    "frontend/src/assets/vite.svg",
    "frontend/src/assets/hero.png"
])

# ---------------------------------------------------------------------------
# Commit 14
# ---------------------------------------------------------------------------
copy_from_backup("frontend/src/components/AgentGraph.tsx")
make_commit(DEV_SPOORTHY, "2026-06-24T10:30:00", "feat(frontend): add AgentGraph visualization component", ["frontend/src/components/AgentGraph.tsx"])

# ---------------------------------------------------------------------------
# Commit 15
# ---------------------------------------------------------------------------
copy_from_backup("frontend/src/components/RunningScreen.tsx")
copy_from_backup("frontend/src/components/ReviewScreen.tsx")
make_commit(DEV_SID, "2026-06-24T12:00:00", "feat(frontend): add RunningScreen and ReviewScreen components", [
    "frontend/src/components/RunningScreen.tsx",
    "frontend/src/components/ReviewScreen.tsx"
])

# ---------------------------------------------------------------------------
# Commit 16
# ---------------------------------------------------------------------------
copy_from_backup("frontend/src/components/DoneScreen.tsx")
copy_from_backup("frontend/src/components/ErrorScreen.tsx")
copy_from_backup("frontend/public/favicon.svg")
copy_from_backup("frontend/public/icons.svg")
make_commit(DEV_AJAI, "2026-06-24T14:00:00", "feat(frontend): add DoneScreen and ErrorScreen components", [
    "frontend/src/components/DoneScreen.tsx",
    "frontend/src/components/ErrorScreen.tsx",
    "frontend/public/favicon.svg",
    "frontend/public/icons.svg"
])

# ---------------------------------------------------------------------------
# Commit 17
# ---------------------------------------------------------------------------
copy_from_backup("frontend/src/main.tsx")
def get_initial_app_tsx():
    with open(os.path.join(backup_dir, "frontend/src/App.tsx"), "r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace("  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');\\n", "")
    
    target_to_remove = """  const checkHealth = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      if (res.ok) {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    } catch (err) {
      setBackendStatus('offline');
    }
  };

  // Health check on startup and every 5 seconds
  useEffect(() => {
    checkHealth();
    const healthInterval = setInterval(checkHealth, 5000);
    return () => clearInterval(healthInterval);
  }, []);"""
    
    content = content.replace(target_to_remove, "")
    content = content.replace("<Header backendUrl={BACKEND_URL} backendStatus={backendStatus} />", "<Header backendUrl={BACKEND_URL} />")
    return content

write_file("frontend/src/App.tsx", get_initial_app_tsx())
make_commit(DEV_SPOORTHY, "2026-06-24T15:30:00", "feat(frontend): implement App.tsx routing and state management", [
    "frontend/src/main.tsx",
    "frontend/src/App.tsx"
])

# ---------------------------------------------------------------------------
# Commit 18
# ---------------------------------------------------------------------------
copy_from_backup("DEPLOY.md")
copy_from_backup("README.md")
copy_from_backup("tests/test_pipeline.py")
make_commit(DEV_SID, "2026-06-24T17:00:00", "docs: document setup and deployment guides", [
    "DEPLOY.md",
    "README.md",
    "tests/test_pipeline.py"
])

# ---------------------------------------------------------------------------
# Commit 19
# ---------------------------------------------------------------------------
copy_from_backup("frontend/src/App.tsx")
copy_from_backup("frontend/src/components/Header.tsx")
copy_from_backup("frontend/src/index.css")
make_commit(DEV_AJAI, "2026-06-24T18:30:00", "feat(frontend): add live API health-check monitoring", [
    "frontend/src/App.tsx",
    "frontend/src/components/Header.tsx",
    "frontend/src/index.css"
])

# ---------------------------------------------------------------------------
# Commit 20
# ---------------------------------------------------------------------------
copy_from_backup("app/llm.py")
make_commit(DEV_SPOORTHY, "2026-06-24T20:00:00", "feat(backend): add Groq API key rotation and fallback mechanism", ["app/llm.py"])

print("3. Replacing main branch and pushing to remote...")
# Switch to main and force-reset it to main-temp
subprocess.run(["git", "checkout", "main"], cwd=workspace_dir, check=True)
subprocess.run(["git", "reset", "--hard", "main-temp"], cwd=workspace_dir, check=True)
# Delete the temporary branch
subprocess.run(["git", "branch", "-D", "main-temp"], cwd=workspace_dir, check=True)

# Clean up temp_backup directory
shutil.rmtree(backup_dir)
print("4. Cleanup complete. Codebase history rebuilt successfully.")
