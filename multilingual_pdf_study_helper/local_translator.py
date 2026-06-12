import json
import re
from pathlib import Path
from typing import Any

from safe_utils import safe_list, safe_string


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_TERM_DICTIONARY_PATH = PROJECT_DIR / "data" / "term_dictionary.json"


def load_term_dictionary(file_path: str | Path = DEFAULT_TERM_DICTIONARY_PATH) -> list[dict]:
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


def get_term_aliases(term: dict) -> list[str]:
    aliases = []
    for key in ["english", "korean", "chinese"]:
        value = safe_string(term.get(key)).strip()
        if value:
            aliases.append(value)

    aliases.extend(
        safe_string(alias).strip()
        for alias in safe_list(term.get("aliases"))
        if safe_string(alias).strip()
    )

    return sorted(set(aliases), key=len, reverse=True)


def get_term_match_score(query_text: Any, term: dict) -> int:
    query_lower = safe_string(query_text).lower()
    if not query_lower:
        return 0

    score = 0
    for alias in get_term_aliases(term):
        alias_lower = alias.lower()
        if alias_lower and alias_lower in query_lower:
            score += max(2, len(alias_lower.split()) * 2)

    return score


def match_terms(query_text: Any, limit: int = 30) -> list[dict]:
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 30

    if limit <= 0:
        return []

    scored_terms = []
    for term in load_term_dictionary():
        score = get_term_match_score(query_text, term)
        if score > 0:
            scored_terms.append((score, term))

    scored_terms.sort(key=lambda pair: pair[0], reverse=True)
    return [term for score, term in scored_terms[:limit]]


def term_to_glossary_item(term: dict) -> dict:
    return {
        "english": safe_string(term.get("english")),
        "korean": safe_string(term.get("korean")),
        "chinese": safe_string(term.get("chinese")),
        "explanation": safe_string(term.get("explanation")),
    }


def build_fast_translation_lines(terms: list[dict], limit: int = 12) -> list[str]:
    lines = []
    for term in terms[:limit]:
        english = safe_string(term.get("english"))
        korean = safe_string(term.get("korean"))
        chinese = safe_string(term.get("chinese"))
        explanation = safe_string(term.get("explanation"))
        subject = safe_string(term.get("subject"))
        label = " / ".join(part for part in [english, korean, chinese] if part)
        if subject:
            label = f"[{subject}] {label}"
        if explanation:
            label = f"{label}: {explanation}"
        if label:
            lines.append(label)
    return lines


def build_translated_preview(query_text: Any, terms: list[dict], max_length: int = 1200) -> str:
    """Annotate matched terms in a short text preview without calling an API."""
    preview = safe_string(query_text)[:max_length]
    if not preview or not terms:
        return preview

    matches = []
    for term in terms:
        korean = safe_string(term.get("korean"))
        chinese = safe_string(term.get("chinese"))
        annotation = " / ".join(part for part in [korean, chinese] if part)
        if not annotation:
            continue

        preview_aliases = [
            safe_string(term.get("english")),
            safe_string(term.get("korean")),
            safe_string(term.get("chinese")),
        ]
        for alias in sorted(set(preview_aliases), key=len, reverse=True):
            alias_text = safe_string(alias).strip()
            if len(alias_text) < 3:
                continue
            flags = re.IGNORECASE if alias_text.isascii() else 0
            match = re.search(re.escape(alias_text), preview, flags=flags)
            if match:
                matches.append(
                    {
                        "start": match.start(),
                        "end": match.end(),
                        "text": preview[match.start() : match.end()],
                        "annotation": annotation,
                    }
                )
                break

    selected_matches = []
    occupied_spans = []
    for match in sorted(matches, key=lambda item: (item["start"], -(item["end"] - item["start"]))):
        overlaps = any(
            not (match["end"] <= start or match["start"] >= end)
            for start, end in occupied_spans
        )
        if overlaps:
            continue
        selected_matches.append(match)
        occupied_spans.append((match["start"], match["end"]))
        if len(selected_matches) >= 20:
            break

    translated_preview = preview
    for match in sorted(selected_matches, key=lambda item: item["start"], reverse=True):
        replacement = f"{match['text']} [{match['annotation']}]"
        translated_preview = (
            translated_preview[: match["start"]]
            + replacement
            + translated_preview[match["end"] :]
        )

    return translated_preview
