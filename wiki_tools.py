import difflib
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

BASE_PATH = "/home/agentascend/projects/AgentAscend"
WIKI_PATH = os.path.join(BASE_PATH, "wiki")

REQUIRED_SECTIONS = [
    "## Summary",
    "## Components",
    "## Relationships",
    "## Notes",
]

WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def _ok(data: Dict) -> Dict:
    return {"status": "ok", **data}


def _error(code: str, message: str, *, hints: List[str] | None = None, **details) -> Dict:
    payload = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "hints": hints or [],
        },
    }
    if details:
        payload["error"]["details"] = details
    return payload


def _page_path(title: str) -> str:
    return os.path.join(WIKI_PATH, f"{title}.md")


def _normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _canonical_title(value: str) -> str:
    normalized = _normalize_title(value).lower()
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _extract_titles() -> List[str]:
    if not os.path.isdir(WIKI_PATH):
        return []

    titles = []
    for filename in os.listdir(WIKI_PATH):
        if filename.endswith(".md"):
            titles.append(filename[:-3])
    return sorted(titles)


def _near_title_matches(title: str, candidates: List[str], threshold: float = 0.84) -> List[Tuple[str, float]]:
    target_canonical = _canonical_title(title)
    matches: List[Tuple[str, float]] = []

    for candidate in candidates:
        candidate_canonical = _canonical_title(candidate)
        score = difflib.SequenceMatcher(None, target_canonical, candidate_canonical).ratio()
        if score >= threshold:
            matches.append((candidate, round(score, 3)))

    return sorted(matches, key=lambda item: item[1], reverse=True)


def validate_wiki_schema(content: str) -> Dict:
    missing = [section for section in REQUIRED_SECTIONS if section not in (content or "")]
    if missing:
        return _error(
            "SCHEMA_VALIDATION_FAILED",
            "Wiki page is missing required schema sections.",
            hints=[
                "Include all required headings: Summary, Components, Relationships, Notes.",
                "Use system/schema.md as the formatting reference.",
            ],
            missing_sections=missing,
        )

    heading_positions = [content.index(section) for section in REQUIRED_SECTIONS]
    if heading_positions != sorted(heading_positions):
        return _error(
            "SCHEMA_SECTION_ORDER_INVALID",
            "Required sections are present but out of order.",
            hints=["Keep section order as: Summary -> Components -> Relationships -> Notes."],
            required_order=REQUIRED_SECTIONS,
        )

    return _ok({"validated": True})


def read_wiki_page(title):
    title = _normalize_title(title)
    path = _page_path(title)

    if not os.path.exists(path):
        return _error(
            "PAGE_NOT_FOUND",
            f"Page '{title}' not found.",
            hints=["Use list_wiki_pages() to inspect available pages."],
            title=title,
        )

    with open(path, "r", encoding="utf-8") as f:
        return _ok({"title": title, "content": f.read()})


def list_wiki_pages():
    return _ok({"pages": _extract_titles()})


def search_wiki_pages(query: str, *, limit: int = 10) -> Dict:
    query_norm = _normalize_title(query)
    if not query_norm:
        return _error(
            "INVALID_QUERY",
            "Search query cannot be empty.",
            hints=["Provide a non-empty concept name or keyword."],
        )

    pages = _extract_titles()
    query_canonical = _canonical_title(query_norm)
    scored: List[Tuple[str, float]] = []
    for page in pages:
        score = difflib.SequenceMatcher(None, query_canonical, _canonical_title(page)).ratio()
        if score >= 0.45:
            scored.append((page, round(score, 3)))

    scored.sort(key=lambda item: item[1], reverse=True)
    return _ok({"query": query_norm, "matches": scored[:limit]})


def create_wiki_page(title: str, content: str) -> Dict:
    title = _normalize_title(title)
    if not title:
        return _error(
            "INVALID_TITLE",
            "Title cannot be empty.",
            hints=["Provide a clear concept title, e.g. 'Payment System'."],
        )

    schema_result = validate_wiki_schema(content)
    if schema_result["status"] == "error":
        return schema_result

    # Enforced search-before-create flow
    search_result = search_wiki_pages(title, limit=5)
    existing_titles = _extract_titles()

    if title in existing_titles:
        return _error(
            "DUPLICATE_TITLE",
            f"A page with title '{title}' already exists.",
            hints=["Use update_wiki_page() instead of create_wiki_page()."],
            related_pages=[title],
            search_result=search_result.get("matches", []),
        )

    near_matches = _near_title_matches(title, existing_titles)
    if near_matches:
        related_pages = [name for name, _score in near_matches[:5]]
        return _error(
            "NEAR_DUPLICATE_TITLE",
            "Creation blocked: this concept is too similar to existing pages.",
            hints=[
                "Review related pages before creating a new concept.",
                "If this is truly new, choose a more specific non-overlapping title.",
            ],
            related_pages=related_pages,
            similarity_scores=near_matches[:5],
            search_result=search_result.get("matches", []),
        )

    path = _page_path(title)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return _ok({"title": title, "path": path, "search_performed": True})


def update_wiki_page(title: str, content: str) -> Dict:
    title = _normalize_title(title)
    if not title:
        return _error("INVALID_TITLE", "Title cannot be empty.")

    schema_result = validate_wiki_schema(content)
    if schema_result["status"] == "error":
        return schema_result

    path = _page_path(title)
    if not os.path.exists(path):
        return _error(
            "PAGE_NOT_FOUND",
            f"Cannot update '{title}' because it does not exist.",
            hints=["Use create_wiki_page() to create new concepts."],
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return _ok({"title": title, "path": path})


def _extract_relationship_links(content: str) -> List[str]:
    if "## Relationships" not in content:
        return []

    section = content.split("## Relationships", 1)[1]
    for next_header in ["\n## Notes", "\n## "]:
        if next_header in section:
            section = section.split(next_header, 1)[0]
            break

    return [match.strip() for match in WIKILINK_PATTERN.findall(section)]


def add_relationship_links(title: str, links: List[str]) -> Dict:
    read_result = read_wiki_page(title)
    if read_result["status"] == "error":
        return read_result

    content = read_result["content"]
    if "## Relationships" not in content:
        return _error(
            "MISSING_RELATIONSHIPS_SECTION",
            f"Page '{title}' is missing the Relationships section.",
            hints=["Add '## Relationships' to comply with schema."],
        )

    existing_links = _extract_relationship_links(content)
    existing_set = {link for link in existing_links}

    incoming = [_normalize_title(link) for link in links if _normalize_title(link)]
    merged = existing_links[:]
    for link in incoming:
        if link not in existing_set:
            merged.append(link)
            existing_set.add(link)

    relationships_block = "\n".join(f"- [[{link}]]" for link in merged)
    if not relationships_block:
        relationships_block = "- [[Knowledge System]]"

    pattern = re.compile(r"## Relationships\n(.*?)(\n## Notes)", re.DOTALL)
    updated_content, count = pattern.subn(f"## Relationships\n{relationships_block}\n\\2", content)
    if count != 1:
        return _error(
            "RELATIONSHIPS_UPDATE_FAILED",
            "Could not safely update Relationships section.",
            hints=["Ensure page contains both '## Relationships' and '## Notes' headings."],
        )

    schema_result = validate_wiki_schema(updated_content)
    if schema_result["status"] == "error":
        return schema_result

    path = _page_path(title)
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated_content)

    return _ok(
        {
            "title": title,
            "path": path,
            "added_links": [link for link in incoming if link in merged and link not in existing_links],
            "final_links": merged,
        }
    )
