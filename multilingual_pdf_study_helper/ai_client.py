import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import openai

from safe_utils import normalize_result, safe_list, safe_string


PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free"
MAX_TEXT_LENGTH = 12000
OPENROUTER_TIMEOUT_SECONDS = 60
AI_FAILURE_DETAILS = (
    "AI 분석을 완료하지 못했습니다. "
    "OpenRouter API 키, 모델명, 인터넷 연결 상태를 확인해주세요."
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


def get_openrouter_api_key() -> str:
    """Read the API key from .env and ignore placeholder values."""
    load_dotenv(ENV_FILE, override=True)
    api_key = safe_string(os.getenv("OPENROUTER_API_KEY")).strip()
    if api_key in API_KEY_PLACEHOLDERS:
        return ""
    return api_key


def get_current_model_info() -> dict[str, Any]:
    """Return the currently configured model and whether the default is used."""
    load_dotenv(ENV_FILE, override=True)
    raw_model = safe_string(os.getenv("OPENROUTER_MODEL")).strip()

    if not raw_model or raw_model in MODEL_PLACEHOLDERS:
        return {
            "model": DEFAULT_MODEL,
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


def build_prompt(
    pdf_text: str,
    knowledge_results: list[dict],
    target_language: str,
    term_mode: str,
) -> str:
    short_pdf_text = safe_string(pdf_text)[:MAX_TEXT_LENGTH]

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
설명 언어는 사용자가 선택한 target_language를 따르세요.
전공 용어 처리 방식은 사용자가 선택한 term_mode를 따르세요.
중요한 전공 용어는 학습에 필요하므로 영어 원어와 번역을 적절히 고려하세요.
예: Linear Independence(선형독립), Basis(기저), Span(생성공간), Rank(랭크)
PDF에 없는 내용을 과장해서 만들지 마세요.
공식이 없다면 "특별히 추출된 공식은 없습니다."라고 작성하세요.
대학교 1학년이 이해할 수 있게 설명하세요.
시험공부에 바로 사용할 수 있게 정리하세요.

반드시 아래 JSON 형식으로만 응답하세요.
마크다운 코드블록은 사용하지 마세요.

{{
  "title": "문서 제목 또는 주제",
  "concepts": ["주요 개념 1", "주요 개념 2"],
  "formulas": ["공식 또는 정의 1", "공식 또는 정의 2"],
  "key_points": ["핵심 내용 1", "핵심 내용 2"],
  "knowledge_references": [
    {{
      "title": "참고한 지식베이스 제목",
      "content": "참고 내용"
    }}
  ],
  "details": "상세 설명",
  "glossary": [
    {{
      "english": "Linear Independence",
      "korean": "선형독립",
      "chinese": "线性无关",
      "explanation": "다른 벡터들의 선형결합으로 표현되지 않는 성질"
    }}
  ],
  "quiz": ["복습 문제 1", "복습 문제 2"]
}}

target_language: {safe_string(target_language)}
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


def test_openrouter_connection() -> dict[str, Any]:
    """Send a very small request to OpenRouter and report connection status."""
    api_key = get_openrouter_api_key()
    model = get_current_model_info()["model"]

    if not api_key:
        return {
            "success": False,
            "message": "OPENROUTER_API_KEY가 설정되지 않았습니다.",
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


def request_chat_completion(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int | None = None,
) -> str:
    """Call OpenRouter with either the modern or legacy OpenAI Python package."""
    messages = [
        {
            "role": "system",
            "content": "You are a careful multilingual study assistant. Return JSON only.",
        },
        {"role": "user", "content": prompt},
    ]

    if hasattr(openai, "OpenAI"):
        client = openai.OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=OPENROUTER_TIMEOUT_SECONDS,
        )
        request_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens

        response = client.chat.completions.create(**request_kwargs)
        return safe_string(response.choices[0].message.content)

    openai.api_key = api_key
    openai.api_base = OPENROUTER_BASE_URL
    request_kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "request_timeout": OPENROUTER_TIMEOUT_SECONDS,
    }
    if max_tokens is not None:
        request_kwargs["max_tokens"] = max_tokens

    response = openai.ChatCompletion.create(**request_kwargs)
    return safe_string(response["choices"][0]["message"]["content"])
