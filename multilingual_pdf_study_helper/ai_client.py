import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
import requests

from safe_utils import normalize_result, safe_list, safe_string


PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
MAX_TEXT_LENGTH = 12000
OPENROUTER_TIMEOUT_SECONDS = 60
OLLAMA_TIMEOUT_SECONDS = 180
AI_FAILURE_DETAILS = (
    "AI 분석을 완료하지 못했습니다. 선택한 AI 모드, 모델명, 연결 상태를 확인해주세요."
)
API_KEY_PLACEHOLDERS = {
    "",
    "여기에_API_KEY_입력",
    "your_api_key_here",
    "your_openrouter_api_key",
}
MODEL_PLACEHOLDERS = {
    "",
    "사용할_모델명_입력",
    "your_model_name",
    "your_model_here",
}


def get_project_env() -> dict[str, Any]:
    if not ENV_FILE.exists():
        return {}
    return dict(dotenv_values(ENV_FILE))


def normalize_openrouter_api_key(value: str | None) -> str:
    """Extract a usable OpenRouter key from pasted text."""
    raw_value = safe_string(value).strip().strip('"').strip("'")
    if raw_value.lower().startswith("bearer "):
        raw_value = raw_value[7:].strip()

    key_match = re_search_openrouter_key(raw_value)
    if key_match:
        return key_match

    return raw_value


def re_search_openrouter_key(value: str) -> str:
    match = re.search(r"sk-or-v1-[A-Za-z0-9_-]+", safe_string(value))
    return match.group(0) if match else ""


def get_openrouter_api_key() -> str:
    """Read the API key from the project .env file only."""
    api_key = normalize_openrouter_api_key(get_project_env().get("OPENROUTER_API_KEY"))
    if api_key in API_KEY_PLACEHOLDERS:
        return ""
    return api_key


def openrouter_key_looks_valid(api_key: str) -> bool:
    return bool(re_search_openrouter_key(api_key))


def get_current_model_info() -> dict[str, Any]:
    """Return the currently configured OpenRouter model."""
    raw_model = safe_string(get_project_env().get("OPENROUTER_MODEL")).strip()

    if raw_model in MODEL_PLACEHOLDERS:
        return {
            "model": DEFAULT_MODEL,
            "uses_default": True,
        }

    return {
        "model": raw_model,
        "uses_default": False,
    }


def get_ollama_model_info() -> dict[str, Any]:
    """Return the configured local Ollama model."""
    raw_model = safe_string(get_project_env().get("OLLAMA_MODEL")).strip()

    if raw_model in MODEL_PLACEHOLDERS:
        return {
            "model": DEFAULT_OLLAMA_MODEL,
            "uses_default": True,
        }

    return {
        "model": raw_model,
        "uses_default": False,
    }


def get_empty_analysis(details: str = "") -> dict[str, Any]:
    return normalize_result(
        {
            "title": "AI 분석 결과",
            "details": details,
        }
    )


def get_output_language_instruction(target_language: str) -> str:
    """Return a clear language instruction without forcing extra languages."""
    language = safe_string(target_language).strip() or "Korean"
    language_map = {
        "Korean": "Korean only",
        "English": "English only",
        "Chinese": "Chinese only",
        "Korean + Chinese": "Korean and Chinese",
        "English + Korean": "English and Korean",
        "English + Chinese": "English and Chinese",
        "English + Korean + Chinese": "English, Korean, and Chinese",
    }
    return language_map.get(language, language)


def build_prompt(
    pdf_text: str,
    knowledge_results: list[dict],
    target_language: str,
    term_mode: str,
) -> str:
    short_pdf_text = safe_string(pdf_text)[:MAX_TEXT_LENGTH]
    output_language = get_output_language_instruction(target_language)

    try:
        knowledge_text = json.dumps(
            safe_list(knowledge_results),
            ensure_ascii=False,
            indent=2,
        )
    except (TypeError, ValueError):
        knowledge_text = "[]"

    return f"""
You are a careful study assistant for lecture PDFs.

Analyze only the content supported by the uploaded PDF text and the optional knowledge-base references.
Do not invent concepts, formulas, examples, or claims that are not supported by the PDF.

Output language:
{output_language}

Important language rules:
- Use only the selected output language(s).
- Do not add Chinese unless the selected output language includes Chinese.
- If Korean only is selected, write Korean only.
- If English only is selected, write English only.
- If Chinese only is selected, write Chinese only.
- In glossary items, leave fields for unselected languages empty.
- The "english" glossary field may contain the original technical term only when useful for studying.

Technical term handling:
{safe_string(term_mode)}

Accuracy rules:
- Preserve numbers, formulas, variables, symbols, and notation as much as possible.
- If a formula is unclear or incomplete in the extracted PDF text, say that the original formula needs checking.
- If no formula is found, write that no formula was extracted.
- Prefer concise, exam-useful explanations.
- When knowledge-base references are provided, use them only when they are relevant to the PDF.

Return JSON only. Do not use Markdown code fences.

{{
  "title": "document title or topic",
  "concepts": ["key concept 1", "key concept 2"],
  "formulas": ["formula or definition 1", "formula or definition 2"],
  "key_points": ["exam key point 1", "exam key point 2"],
  "knowledge_references": [
    {{
      "title": "reference title",
      "content": "reference content"
    }}
  ],
  "details": "detailed explanation",
  "glossary": [
    {{
      "english": "Linear Independence",
      "korean": "선형독립",
      "chinese": "",
      "explanation": "short explanation in the selected output language"
    }}
  ],
  "quiz": ["review question 1", "review question 2"]
}}

target_language: {safe_string(target_language)}
output_language: {output_language}
term_mode: {safe_string(term_mode)}

[PDF text]
{short_pdf_text}

[Knowledge-base references]
{knowledge_text}
""".strip()


def strip_markdown_code_block(response_text: str) -> str:
    text = safe_string(response_text).strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text


def parse_json_response(response_text: str) -> dict[str, Any]:
    cleaned_text = strip_markdown_code_block(response_text)

    try:
        data = json.loads(cleaned_text)
    except (json.JSONDecodeError, TypeError):
        return get_empty_analysis(
            "AI 응답을 JSON으로 변환하지 못했습니다. 아래 원문 응답을 확인하세요.\n\n"
            f"{safe_string(response_text)}"
        )

    return normalize_result(data)


def call_openrouter_ai(
    pdf_text: str,
    knowledge_results: list[dict],
    target_language: str,
    term_mode: str,
) -> dict[str, Any]:
    api_key = get_openrouter_api_key()
    model = get_current_model_info()["model"]

    if not api_key:
        return normalize_result(
            {
                "error": (
                    "OPENROUTER_API_KEY가 설정되지 않았습니다. "
                    ".env 파일에 실제 API 키를 입력해주세요."
                ),
                "details": AI_FAILURE_DETAILS,
            }
        )
    if not openrouter_key_looks_valid(api_key):
        return normalize_result(
            {
                "error": "OPENROUTER_API_KEY 형식이 올바르지 않습니다. OpenRouter 키는 보통 sk-or-v1- 로 시작합니다.",
                "details": AI_FAILURE_DETAILS,
            }
        )

    try:
        prompt = build_prompt(
            pdf_text=pdf_text,
            knowledge_results=knowledge_results,
            target_language=target_language,
            term_mode=term_mode,
        )
    except Exception as error:
        return normalize_result(
            {
                "error": f"AI 프롬프트를 만드는 중 오류가 발생했습니다: {error}",
                "details": "PDF 텍스트 또는 지식베이스 값을 처리하지 못했습니다.",
            }
        )

    try:
        response_text = request_chat_completion(api_key, model, prompt)
    except Exception as error:
        return normalize_result(
            {
                "error": f"OpenRouter API 호출에 실패했습니다: {error}",
                "details": AI_FAILURE_DETAILS,
            }
        )

    return parse_json_response(response_text)


def call_ollama_ai(
    pdf_text: str,
    knowledge_results: list[dict],
    target_language: str,
    term_mode: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Run the same AI analysis through local Ollama without an API key."""
    model_name = safe_string(model).strip() or get_ollama_model_info()["model"]

    try:
        prompt = build_prompt(
            pdf_text=pdf_text,
            knowledge_results=knowledge_results,
            target_language=target_language,
            term_mode=term_mode,
        )
    except Exception as error:
        return normalize_result(
            {
                "error": f"Ollama 프롬프트를 만드는 중 오류가 발생했습니다: {error}",
                "details": "PDF 텍스트 또는 지식베이스 값을 처리하지 못했습니다.",
            }
        )

    try:
        response_text = request_ollama_completion(model_name, prompt)
    except Exception as error:
        return normalize_result(
            {
                "error": f"Ollama 호출에 실패했습니다: {error}",
                "details": "Ollama가 설치되어 있고 실행 중인지 확인해주세요. 예: ollama serve, ollama pull qwen2.5:7b",
            }
        )

    return parse_json_response(response_text)


def test_openrouter_connection() -> dict[str, Any]:
    """Send a small request to OpenRouter and report connection status."""
    api_key = get_openrouter_api_key()
    model = get_current_model_info()["model"]

    if not api_key:
        return {
            "success": False,
            "message": "OPENROUTER_API_KEY가 설정되지 않았습니다.",
        }
    if not openrouter_key_looks_valid(api_key):
        return {
            "success": False,
            "message": "API Key 형식이 올바르지 않습니다. OpenRouter 키는 보통 sk-or-v1- 로 시작합니다.",
        }

    try:
        response_text = request_chat_completion(
            api_key=api_key,
            model=model,
            prompt="Reply with OK only.",
            max_tokens=5,
        )
    except Exception as error:
        return {
            "success": False,
            "message": safe_string(error) or "OpenRouter 연결 테스트 중 오류가 발생했습니다.",
        }

    if response_text.strip():
        return {
            "success": True,
            "message": "OpenRouter 연결 성공",
        }

    return {
        "success": False,
        "message": "OpenRouter가 빈 응답을 반환했습니다.",
    }


def test_ollama_connection(model: str | None = None) -> dict[str, Any]:
    """Check whether the local Ollama server can answer a tiny request."""
    model_name = safe_string(model).strip() or get_ollama_model_info()["model"]

    try:
        response_text = request_ollama_completion(
            model=model_name,
            prompt="Reply with OK only.",
        )
    except Exception as error:
        return {
            "success": False,
            "message": safe_string(error) or "Ollama 연결 테스트 중 오류가 발생했습니다.",
        }

    if response_text.strip():
        return {
            "success": True,
            "message": f"Ollama 연결 성공: {model_name}",
        }

    return {
        "success": False,
        "message": "Ollama가 빈 응답을 반환했습니다.",
    }


def request_ollama_completion(model: str, prompt: str) -> str:
    """Call the local Ollama generate API."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
        },
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )

    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = response.text
        raise RuntimeError(f"오류 코드 {response.status_code}: {error_payload}")

    data = response.json()
    return safe_string(data.get("response"))


def request_chat_completion(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int | None = None,
) -> str:
    """Call OpenRouter with an explicit Authorization header."""
    messages = [
        {
            "role": "system",
            "content": "You are a careful multilingual study assistant. Return JSON only.",
        },
        {"role": "user", "content": prompt},
    ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8502",
            "X-Title": "Multilingual PDF Study Helper",
        },
        json=payload,
        timeout=OPENROUTER_TIMEOUT_SECONDS,
    )

    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = response.text
        raise RuntimeError(f"오류 코드 {response.status_code}: {error_payload}")

    data = response.json()
    return safe_string(data["choices"][0]["message"]["content"])
