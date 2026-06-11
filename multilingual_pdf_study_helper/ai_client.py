import ast
import json
import os
import re
import warnings
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
MAX_TEXT_LENGTH = 20000
ANALYSIS_MAX_TOKENS = 7000
OPENROUTER_TIMEOUT_SECONDS = 60
OLLAMA_TIMEOUT_SECONDS = 180
AI_FAILURE_DETAILS = (
    "AI 분석을 완료하지 못했습니다. 선택한 AI 모드, 모델명, 연결 상태를 확인해주세요."
)
LATEX_JSON_COMMAND_PATTERN = (
    r"(?:frac|sqrt|sum|int|lim|partial|cdot|times|omega|Omega|Phi|phi|theta|Theta|"
    r"lambda|Lambda|alpha|beta|gamma|Gamma|Delta|delta|sigma|Sigma|mu|pi|Pi|rho|"
    r"epsilon|varepsilon|infty|nabla|mathrm|mathbf|mathit|text|left|right|sin|cos|"
    r"tan|log|ln|exp|leq|geq|neq|approx|pm|mp|div|to|rightarrow|leftarrow|Rightarrow|"
    r"Leftarrow|cdots|ldots|begin|end|overline|underline|hat|bar|vec|dot|ddot)\b"
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
This app must work for any course field, including math, science, engineering, humanities, arts, language learning, social science, business, and presentation materials.

Output language:
{output_language}

Important language rules:
- Use only the selected output language(s).
- Do not add Chinese unless the selected output language includes Chinese.
- If Korean only is selected, write Korean only.
- If English only is selected, write English only.
- If Chinese only is selected, write Chinese only.
- Exception: the glossary is always multilingual. Fill english, korean, and chinese for every glossary item.
- In the glossary explanation field, use the selected output language(s).

Technical term handling:
{safe_string(term_mode)}

Accuracy rules:
- Adapt the analysis to the PDF's actual field. For non-math PDFs, focus on definitions, frameworks, arguments, evidence, procedures, vocabulary, examples, and discussion points.
- Preserve numbers, formulas, variables, symbols, and notation as much as possible.
- Preserve formulas close to the PDF original and display them as proper LaTeX math whenever possible.
- In every output field, including concepts, key_points, details, quiz, answers, explanations, and formulas, render mathematical expressions in LaTeX between dollar signs whenever possible.
- In the formulas field, put the main formula in LaTeX between dollar signs, such as "$E_k = \\\\frac{{1}}{{2}}mv^2$" in the raw JSON text.
- Use LaTeX for fractions, powers, subscripts, Greek letters, matrices, integrals, summations, and derivatives whenever they appear in the PDF.
- Do not force equations or mathematical notation if the PDF is not mathematical.
- Avoid plain text formulas like "1/2x^2" unless the original PDF formula is too unclear to reconstruct. If plain text is unavoidable, add spaces and parentheses.
- Explain what each symbol means right after the formula when possible.
- If a formula is unclear or incomplete in the extracted PDF text, say that the original formula needs checking.
- If no formula is found, use the formulas field for important definitions, models, frameworks, procedures, or key terminology instead.
- Be detailed enough that a student can actually study from the result.
- When knowledge-base references are provided, use them only when they are relevant to the PDF.
- Do not stop after a short summary. Explain relationships between concepts, why they matter, and how they are used.
- Turn the PDF into a study guide, not just a summary.
- Prefer concrete explanations over vague statements.
- When the PDF provides enough context, include the learning flow: prerequisite idea -> main concept -> formula/definition -> how to apply -> common mistake.
- If examples are present in the PDF, explain them step by step. If examples are not present, do not invent numerical examples; instead describe how an example would be solved in general terms.

Depth requirements:
- concepts: provide 6 to 10 items when the PDF has enough content. Each item should include what it means and why it matters.
- formulas: provide 4 to 10 formulas, definitions, models, frameworks, procedures, or key terminology items when available. Use equations only when the PDF actually contains them.
- key_points: provide 6 to 12 exam-oriented points. Include common traps, required assumptions, and how to recognize problem types when possible.
- details: write 6 to 10 substantial paragraphs or bullet-style paragraphs. Include definitions, intuition, relationships between concepts, application procedure, and common mistakes.
- glossary: provide 8 to 15 important terms when possible, always with english, korean, and chinese filled.
- quiz: provide 6 to 12 review questions, including conceptual questions, application/scenario questions, discussion questions, and short answer questions when possible. Each quiz item must include question, answer, and explanation.
- In quiz questions, answers, and explanations, render any formula or mathematical expression in LaTeX between dollar signs.
- knowledge_references: include the relevant references you actually used, and briefly explain why each is relevant.

Return JSON only. Do not use Markdown code fences.
JSON safety rules:
- Use LaTeX math inside JSON strings for every mathematical expression, not only the formulas field.
- Escape LaTeX backslashes as two backslashes in the raw JSON text. Example: "$E_k = \\\\frac{{1}}{{2}}mv^2$".
- Do not output raw single-backslash LaTeX commands inside JSON strings.
- If plain text formulas are unavoidable, use parentheses and spacing. Example: "E_k = (1/2) m v^2".

{{
  "title": "document title or topic",
  "concepts": ["key concept 1: meaning, importance, and relation to the PDF", "key concept 2: meaning, importance, and relation to the PDF"],
  "formulas": ["important formula, definition, model, framework, procedure, or key term from the PDF", "if the PDF includes equations, preserve them in LaTeX such as $E_k = \\\\frac{{1}}{{2}}mv^2$"],
  "key_points": ["exam key point 1 with why it matters and common mistake", "exam key point 2 with how to apply it"],
  "knowledge_references": [
    {{
      "title": "reference title",
      "content": "reference content and why it is relevant"
    }}
  ],
  "details": "a study-guide style explanation with definitions, intuition, relationships, procedures, and common mistakes",
  "glossary": [
    {{
      "english": "Linear Independence",
      "korean": "선형독립",
      "chinese": "线性无关",
      "explanation": "short explanation in the selected output language"
    }}
  ],
  "quiz": [
    {{
      "question": "conceptual review question",
      "answer": "answer hidden by default in the app, using LaTeX for formulas such as $E_k = \\\\frac{{1}}{{2}}mv^2$",
      "explanation": "brief explanation or solving steps, with math rendered in LaTeX when needed"
    }}
  ]
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
    text = re.sub(r"^\s*```(?:json|JSON)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def extract_json_object(response_text: str) -> str:
    """Return the first balanced JSON-looking object from a response."""
    text = safe_string(response_text).strip()
    start = text.find("{")
    if start == -1:
        return text

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        character = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1].strip()

    return text[start:].strip()


def normalize_jsonish_text(json_text: str) -> str:
    """Clean common AI wrapper characters without changing the content meaning."""
    text = safe_string(json_text).strip().lstrip("\ufeff")
    text = text.replace("“", '"').replace("”", '"')
    return text


def remove_trailing_commas(json_text: str) -> str:
    """Remove commas before closing braces/brackets, a common model mistake."""
    return re.sub(r",(\s*[}\]])", r"\1", safe_string(json_text))


def close_unclosed_json(json_text: str) -> str:
    """Best-effort close for responses cut near the end of a JSON object."""
    text = safe_string(json_text).rstrip()
    if not text.startswith("{"):
        return text

    stack: list[str] = []
    in_string = False
    escaped = False

    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            stack.append("}")
        elif character == "[":
            stack.append("]")
        elif character in "}]":
            if stack and stack[-1] == character:
                stack.pop()

    if escaped:
        text += "\\"
    if in_string:
        text += '"'
    while stack:
        text += stack.pop()

    return text


def escape_latex_backslashes(json_text: str) -> str:
    """Escape common LaTeX-style backslashes that break JSON parsing."""
    return re.sub(
        rf"(?<!\\)\\(?={LATEX_JSON_COMMAND_PATTERN})",
        r"\\\\",
        safe_string(json_text),
    )


def escape_invalid_json_backslashes(json_text: str) -> str:
    """Escape non-JSON backslash sequences while preserving valid JSON escapes."""
    return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", safe_string(json_text))


def build_json_candidates(response_text: str) -> list[str]:
    cleaned_text = strip_markdown_code_block(response_text)
    extracted_text = extract_json_object(cleaned_text)
    base_texts = [cleaned_text, extracted_text]
    candidates: list[str] = []

    for base_text in base_texts:
        normalized_text = normalize_jsonish_text(base_text)
        closed_text = close_unclosed_json(normalized_text)
        for candidate in [normalized_text, closed_text]:
            if not candidate:
                continue
            without_trailing_commas = remove_trailing_commas(candidate)
            latex_escaped = escape_latex_backslashes(without_trailing_commas)
            candidates.extend(
                [
                    latex_escaped,
                    escape_invalid_json_backslashes(without_trailing_commas),
                    escape_invalid_json_backslashes(latex_escaped),
                    without_trailing_commas,
                    candidate,
                ]
            )

    return candidates


def parse_json_candidate(candidate: str) -> dict[str, Any] | None:
    try:
        data = json.loads(candidate, strict=False)
    except (json.JSONDecodeError, TypeError):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                data = ast.literal_eval(candidate)
        except (SyntaxError, ValueError, TypeError):
            return None

    if isinstance(data, dict):
        return data
    return None


def load_json_with_repairs(response_text: str) -> dict[str, Any]:
    seen = set()
    for candidate in build_json_candidates(response_text):
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        data = parse_json_candidate(candidate)
        if data is not None:
            return data

    cleaned_text = strip_markdown_code_block(response_text)
    raise json.JSONDecodeError("Could not parse repaired JSON", cleaned_text, 0)


def parse_json_response(response_text: str) -> dict[str, Any]:
    try:
        data = load_json_with_repairs(response_text)
    except (json.JSONDecodeError, TypeError):
        return get_empty_analysis(
            "AI 응답의 JSON 형식이 일부 깨져 구조화 표시를 하지 못했습니다. "
            "아래에 원문 응답을 표시합니다. 다시 분석하면 정상 처리될 수 있습니다.\n\n"
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
        response_text = request_chat_completion(
            api_key,
            model,
            prompt,
            max_tokens=ANALYSIS_MAX_TOKENS,
        )
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
        "temperature": 0.1,
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
