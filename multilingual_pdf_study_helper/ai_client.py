import json
import os
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
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
MAX_TEXT_LENGTH = 12000
OPENROUTER_TIMEOUT_SECONDS = 60
OLLAMA_TIMEOUT_SECONDS = 180
AI_FAILURE_DETAILS = (
    "AI 분석을 완료하지 못했습니다. "
    "선택한 AI 모드, 모델명, 연결 상태를 확인해주세요."
)
API_KEY_PLACEHOLDERS = {
    "your_api_key_here",
    "여기에_API_KEY_입력",
    "your_openrouter_api_key",
}
MODEL_PLACEHOLDERS = {
    "사용할_모델명_입력",
    "your_model_name",
    "your_model_here",
}


def normalize_openrouter_api_key(value: str) -> str:
    """Extract a usable OpenRouter key from pasted text."""
    raw_value = safe_string(value).strip().strip('"').strip("'")
    if raw_value.lower().startswith("bearer "):
        raw_value = raw_value[7:].strip()

    key_match = re_search_openrouter_key(raw_value)
    if key_match:
        return key_match

    return raw_value


def re_search_openrouter_key(value: str) -> str:
    import re

    match = re.search(r"sk-or-v1-[A-Za-z0-9_-]+", value)
    return match.group(0) if match else ""


def get_openrouter_api_key() -> str:
    """Read the API key from the project .env file only."""
    if not ENV_FILE.exists():
        return ""

    env_values = dotenv_values(ENV_FILE)
    api_key = normalize_openrouter_api_key(env_values.get("OPENROUTER_API_KEY", ""))
    placeholders = API_KEY_PLACEHOLDERS | {"", "여기에_API_KEY_입력"}
    if api_key in placeholders:
        return ""
    return api_key


def openrouter_key_looks_valid(api_key: str) -> bool:
    return bool(re_search_openrouter_key(api_key))


def get_current_model_info() -> dict[str, Any]:
    """Return the currently configured model and whether the default is used."""
    env_values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    raw_model = safe_string(env_values.get("OPENROUTER_MODEL")).strip()

    if not raw_model or raw_model in MODEL_PLACEHOLDERS:
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
    env_values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    raw_model = safe_string(env_values.get("OLLAMA_MODEL")).strip()

    if not raw_model or raw_model in MODEL_PLACEHOLDERS:
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


def ensure_chinese_output_language(target_language: str) -> str:
    """Always include Chinese in generated study text."""
    language = safe_string(target_language).strip()
    if "중국어" in language or "Chinese" in language or "中文" in language:
        return language or "중국어"
    if language:
        return f"{language} + 중국어"
    return "중국어"


def build_prompt(
    pdf_text: str,
    knowledge_results: list[dict],
    target_language: str,
    term_mode: str,
) -> str:
    short_pdf_text = safe_string(pdf_text)[:MAX_TEXT_LENGTH]
    output_language = ensure_chinese_output_language(target_language)

    try:
        knowledge_text = json.dumps(
            safe_list(knowledge_results),
            ensure_ascii=False,
            indent=2,
        )
    except (TypeError, ValueError):
        knowledge_text = "[]"

    return f"""
당신은 외국어 강의자료를 분석해주는 다국어 학습 도우미입니다.

사용자가 업로드한 PDF 내용을 바탕으로 분석해야 합니다.
추가로 제공된 지식베이스 참고자료가 있으면 함께 사용하세요.
설명 언어는 아래 output_language를 따르세요.
중요: 사용자가 어떤 언어를 선택해도 번역/정리된 텍스트에는 반드시 중국어(中文)를 함께 포함하세요.
개념, 공식 설명, 핵심 내용, 상세 설명, 복습 문제에는 중국어 번역 또는 중국어 설명을 함께 넣으세요.
중국어만 단독으로 쓰지 말고, 선택 언어가 English 또는 한국어이면 선택 언어 + 中文 형태로 병기하세요.
전공 용어 처리 방식은 사용자가 선택한 term_mode를 따르세요.
중요한 전공 용어는 학습에 필요하므로 영어 원어와 번역을 적절히 고려하세요.
예: Linear Independence(선형독립 / 线性无关), Basis(기저 / 基), Span(생성공간 / 张成空间), Rank(랭크 / 秩)
PDF에 없는 내용을 과장해서 만들지 마세요.
공식이 없다면 "특별히 추출된 공식은 없습니다."라고 작성하세요.
숫자, 공식, 변수명, 첨자, 지수는 원문 의미를 최대한 보존하세요.
예: x^2, a_1, A^{-1}, 2x + 3 = 7 같은 표현을 임의로 바꾸지 마세요.
PDF 추출 과정에서 공식 일부가 불완전해 보이면 단정하지 말고 "원문 공식 확인 필요"라고 표시하세요.
대학교 1학년이 이해할 수 있게 설명하세요.
시험공부에 바로 사용할 수 있게 정리하세요.

반드시 아래 JSON 형식으로만 응답하세요.
마크다운 코드블록은 사용하지 마세요.

{{
  "title": "문서 제목 또는 주제",
  "concepts": ["주요 개념 1 / 中文概念 1", "주요 개념 2 / 中文概念 2"],
  "formulas": ["공식 또는 정의 1 + 중국어 설명", "공식 또는 정의 2 + 中文说明"],
  "key_points": ["핵심 내용 1 / 中文要点 1", "핵심 내용 2 / 中文要点 2"],
  "knowledge_references": [
    {{
      "title": "참고한 지식베이스 제목",
      "content": "참고 내용"
    }}
  ],
  "details": "상세 설명. 반드시 중국어 설명도 함께 포함하세요.",
  "glossary": [
    {{
      "english": "Linear Independence",
      "korean": "선형독립",
      "chinese": "线性无关",
      "explanation": "다른 벡터들의 선형결합으로 표현되지 않는 성질"
    }}
  ],
  "quiz": ["복습 문제 1 / 中文复习题 1", "복습 문제 2 / 中文复习题 2"]
}}

target_language: {safe_string(target_language)}
output_language: {output_language}
term_mode: {safe_string(term_mode)}

[PDF 텍스트]
{short_pdf_text}

[지식베이스 참고자료]
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
                    "프로젝트 폴더에 .env 파일을 만들고 실제 API 키를 입력해주세요."
                ),
                "details": AI_FAILURE_DETAILS,
            }
        )
    if not openrouter_key_looks_valid(api_key):
        return normalize_result(
            {
                "error": (
                    "OPENROUTER_API_KEY 형식이 올바르지 않습니다. "
                    "OpenRouter 키는 보통 sk-or-v1- 로 시작합니다."
                ),
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
                "details": (
                    "Ollama가 설치되어 있고 실행 중인지 확인해주세요. "
                    "예: ollama serve, ollama pull qwen2.5:7b"
                ),
            }
        )

    return parse_json_response(response_text)


def test_openrouter_connection() -> dict[str, Any]:
    """Send a very small request to OpenRouter and report connection status."""
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
