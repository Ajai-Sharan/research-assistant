"""ArXiv search adapter.

We use the public ArXiv REST API because it requires no auth, is rate-friendly
and returns deterministic Atom XML. Semantic Scholar can be plugged in by
implementing the same `search_papers` signature.
"""
from __future__ import annotations

import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Iterable

import requests

from .state import PaperRecord

log = logging.getLogger(__name__)

ARXIV_ENDPOINT = "http://export.arxiv.org/api/query"
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def _parse_entry(entry: ET.Element, source_query: str) -> PaperRecord:
    def text(tag: str) -> str:
        node = entry.find(f"a:{tag}", ATOM_NS)
        return (node.text or "").strip() if node is not None else ""

    authors = [
        (a.findtext("a:name", default="", namespaces=ATOM_NS) or "").strip()
        for a in entry.findall("a:author", ATOM_NS)
    ]
    full_id = text("id")
    # Strip the version suffix for a stable key (e.g. "2401.01234v2" -> "2401.01234")
    paper_id = full_id.rsplit("/", 1)[-1]

    return PaperRecord(
        paper_id=paper_id,
        title=" ".join(text("title").split()),
        authors=[a for a in authors if a],
        abstract=" ".join(text("summary").split()),
        url=full_id,
        published=text("published"),
        source_query=source_query,
    )


def search_arxiv(query: str, max_results: int = 4, timeout: int = 20) -> list[PaperRecord]:
    """Fetch top `max_results` papers from ArXiv for a query.

    Errors are logged and an empty list is returned -- the graph treats a
    barren sub-query as non-fatal so other branches can still produce output.
    """
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_ENDPOINT}?{urllib.parse.urlencode(params)}"
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "research-assistant/1.0"})
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("ArXiv request failed for %r: %s", query, exc)
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as exc:
        log.warning("ArXiv returned malformed XML for %r: %s", query, exc)
        return []

    entries = root.findall("a:entry", ATOM_NS)
    return [_parse_entry(e, source_query=query) for e in entries]


def search_semantic_scholar(query: str, max_results: int = 4, timeout: int = 15) -> list[PaperRecord]:
    """Fetch top `max_results` papers from Semantic Scholar for a query."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
        "fields": "paperId,title,authors,abstract,url,year",
    }
    try:
        resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "research-assistant/1.0"})
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", []):
            paper_id = item.get("paperId", "")
            title = item.get("title", "")
            abstract = item.get("abstract") or ""
            url_val = item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"
            authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
            year = item.get("year")
            published = str(year) if year is not None else ""
            
            results.append(PaperRecord(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract,
                url=url_val,
                published=published,
                source_query=query
            ))
        return results
    except Exception as exc:
        log.warning("Semantic Scholar request failed for %r: %s", query, exc)
        return []


def search_papers(query: str, max_results: int = 4, timeout: int = 20) -> list[PaperRecord]:
    """Fetch top papers trying Semantic Scholar first, and falling back to ArXiv."""
    log.info("Searching Semantic Scholar for query %r", query)
    papers = search_semantic_scholar(query, max_results=max_results, timeout=timeout)
    if papers:
        log.info("Semantic Scholar returned %d results for %r", len(papers), query)
        return papers
        
    log.info("Semantic Scholar returned 0 results, falling back to ArXiv for query %r", query)
    return search_arxiv(query, max_results=max_results, timeout=timeout)


def dedupe_papers(papers: Iterable[PaperRecord]) -> list[PaperRecord]:
    """De-duplicate papers across sub-queries, preserving first-seen order."""
    seen: set[str] = set()
    out: list[PaperRecord] = []
    for paper in papers:
        key = paper.get("paper_id") or paper.get("url", "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(paper)
    return out
