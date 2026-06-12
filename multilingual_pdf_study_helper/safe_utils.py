from typing import Any
import re


DEFAULT_RESULT = {
    "title": "AI 분석 결과",
    "concepts": [],
    "formulas": [],
    "key_points": [],
    "knowledge_references": [],
    "details": "",
    "glossary": [],
    "quiz": [],
}


def safe_string(value: Any) -> str:
    """Convert any value to a display-safe string."""
    if value is None:
        return ""

    try:
        return str(value)
    except Exception:
        return ""


def add_multilingual_spacing(text: Any) -> str:
    """Add readable spaces between Latin, numbers, Chinese, Korean, and Japanese text."""
    value = safe_string(text)
    if not value:
        return ""

    han = r"\u3400-\u4dbf\u4e00-\u9fff"
    hangul = r"\u1100-\u11ff\u3130-\u318f\uac00-\ud7af"
    kana = r"\u3040-\u30ff"
    cjk = han + hangul + kana
    latin_number = r"A-Za-z0-9"

    value = re.sub(rf"([{cjk}])([{latin_number}])", r"\1 \2", value)
    value = re.sub(rf"([{latin_number}])([{cjk}])", r"\1 \2", value)
    value = re.sub(rf"([{han}])([{hangul}{kana}])", r"\1 \2", value)
    value = re.sub(rf"([{hangul}{kana}])([{han}])", r"\1 \2", value)
    value = re.sub(r"([。！？；，、])(?=\S)", r"\1 ", value)
    value = re.sub(r"([!?;])(?=[A-Za-z\u3400-\u4dbf\u4e00-\u9fff\u1100-\u11ff\u3130-\u318f\uac00-\ud7af])", r"\1 ", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value


def safe_list(value: Any) -> list:
    """Convert missing, scalar, or malformed values to a list."""
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple) or isinstance(value, set):
        return list(value)

    if isinstance(value, str):
        stripped_value = value.strip()
        return [stripped_value] if stripped_value else []

    return [value]


def safe_dict(value: Any) -> dict:
    """Return a dictionary or an empty dictionary for malformed values."""
    if isinstance(value, dict):
        return value
    return {}


def normalize_reference(value: Any) -> dict:
    reference = safe_dict(value)
    if not reference:
        return {
            "title": "참고 자료",
            "content": safe_string(value),
            "source_url": "",
        }

    return {
        "title": safe_string(reference.get("title")) or "참고 자료",
        "content": safe_string(reference.get("content")),
        "source_url": safe_string(reference.get("source_url")),
    }


def normalize_glossary_item(value: Any) -> dict:
    item = safe_dict(value)
    if not item:
        text = safe_string(value)
        return {
            "english": text,
            "korean": "",
            "chinese": "",
            "explanation": "",
        }

    return {
        "english": safe_string(item.get("english")),
        "korean": safe_string(item.get("korean")),
        "chinese": safe_string(item.get("chinese")),
        "explanation": safe_string(item.get("explanation")),
    }


def normalize_quiz_item(value: Any) -> dict:
    item = safe_dict(value)
    if not item:
        return {
            "question": safe_string(value),
            "answer": "",
            "explanation": "",
        }

    question = (
        safe_string(item.get("question"))
        or safe_string(item.get("q"))
        or safe_string(item.get("prompt"))
    )
    answer = (
        safe_string(item.get("answer"))
        or safe_string(item.get("a"))
        or safe_string(item.get("solution"))
    )
    explanation = safe_string(item.get("explanation")) or safe_string(item.get("reason"))

    return {
        "question": question,
        "answer": answer,
        "explanation": explanation,
    }


def normalize_result(result: Any) -> dict:
    """Fill missing AI result fields and normalize malformed field types."""
    data = DEFAULT_RESULT.copy()

    if isinstance(result, dict):
        data.update(result)
    else:
        data["details"] = safe_string(result)

    data["title"] = safe_string(data.get("title")) or "AI 분석 결과"
    data["details"] = safe_string(data.get("details"))

    for key in ["concepts", "formulas", "key_points"]:
        data[key] = [safe_string(item) for item in safe_list(data.get(key)) if safe_string(item)]

    data["quiz"] = [
        item
        for item in [normalize_quiz_item(item) for item in safe_list(data.get("quiz"))]
        if item.get("question") or item.get("answer")
    ]

    data["knowledge_references"] = [
        normalize_reference(item) for item in safe_list(data.get("knowledge_references"))
    ]

    data["glossary"] = [
        normalize_glossary_item(item) for item in safe_list(data.get("glossary"))
    ]

    if "error" in data:
        data["error"] = safe_string(data.get("error"))

    if "warning" in data:
        data["warning"] = safe_string(data.get("warning"))

    return data
