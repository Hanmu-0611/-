import json
from pathlib import Path
from typing import Any

from safe_utils import safe_list, safe_string


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_KNOWLEDGE_BASE_PATH = PROJECT_DIR / "data" / "knowledge_base_sample.json"


def load_knowledge_base(file_path: str | Path = DEFAULT_KNOWLEDGE_BASE_PATH) -> list[dict]:
    """Load knowledge-base items from a JSON file without stopping the app."""
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        return []

    try:
        with path.open("r", encoding="utf-8") as json_file:
            data = json.load(json_file)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def get_keyword_score(query_text: Any, item: dict) -> int:
    """Score an item by simple keyword matching."""
    query_lower = safe_string(query_text).lower()
    if not query_lower:
        return 0

    score = 0

    for keyword in safe_list(item.get("keywords")):
        keyword_text = safe_string(keyword).lower().strip()
        if keyword_text and keyword_text in query_lower:
            score += 3

    title = safe_string(item.get("title")).lower()
    if title and title in query_lower:
        score += 2

    content_words = set(safe_string(item.get("content")).lower().split())
    query_words = set(query_lower.split())
    score += len(content_words.intersection(query_words))

    return score


def search_knowledge_base(query_text: Any, top_k: int = 5) -> list[dict]:
    """Return the most relevant knowledge-base items for the PDF text."""
    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 5

    if top_k <= 0:
        return []

    try:
        knowledge_items = load_knowledge_base()
    except Exception:
        return []

    scored_items = []

    for item in knowledge_items:
        try:
            score = get_keyword_score(query_text, item)
        except Exception:
            score = 0

        if score > 0:
            scored_items.append((score, item))

    scored_items.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in scored_items[:top_k]]
