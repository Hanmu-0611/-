from ai_client import MAX_TEXT_LENGTH, call_ollama_ai, call_openrouter_ai
from knowledge_base import search_knowledge_base
from pdf_extractor import extract_pdf_document
from safe_utils import normalize_result, safe_string


EMPTY_PDF_MESSAGE = (
    "PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 스캔 PDF이거나 "
    "텍스트가 포함되지 않은 PDF일 수 있습니다."
)
AI_FAILURE_DETAILS = (
    "AI 분석을 완료하지 못했습니다. 선택한 AI 모드, 모델명, 연결 상태를 확인해주세요."
)
PDF_PREVIEW_LENGTH = 2000
AI_PROVIDER_LABELS = {
    "local": "Local analysis",
    "ollama": "Ollama local AI",
    "openrouter": "OpenRouter online AI",
}


def get_local_text(target_language: str) -> dict[str, str]:
    language = safe_string(target_language)
    if language == "Korean + Chinese":
        return {
            "title": "로컬 분석 결과 / 本地分析结果",
            "matched": "PDF 내용과 관련된 지식베이스 항목을 자동으로 찾았습니다. / 已根据 PDF 内容自动找到相关知识库条目。",
            "local": "OpenRouter API 키 없이 실행한 로컬 분석입니다. / 这是没有 OpenRouter API Key 的本地分析。",
            "details": "AI 요약 없이 로컬에서 만든 결과입니다. / 此结果是在本地生成的，没有使用 AI 摘要。",
            "preview": "PDF 미리보기 / PDF 预览",
            "item": "지식베이스 항목 / 知识库条目",
        }
    if language == "English + Korean":
        return {
            "title": "Local analysis result / 로컬 분석 결과",
            "matched": "Relevant knowledge-base items were found automatically from the PDF. / PDF 내용과 관련된 지식베이스 항목을 자동으로 찾았습니다.",
            "local": "This is a local analysis without an OpenRouter API key. / OpenRouter API 키 없이 실행한 로컬 분석입니다.",
            "details": "This result was created locally without AI summarization. / AI 요약 없이 로컬에서 만든 결과입니다.",
            "preview": "PDF preview / PDF 미리보기",
            "item": "Knowledge-base item / 지식베이스 항목",
        }
    if language == "English + Chinese":
        return {
            "title": "Local analysis result / 本地分析结果",
            "matched": "Relevant knowledge-base items were found automatically from the PDF. / 已根据 PDF 内容自动找到相关知识库条目。",
            "local": "This is a local analysis without an OpenRouter API key. / 这是没有 OpenRouter API Key 的本地分析。",
            "details": "This result was created locally without AI summarization. / 此结果是在本地生成的，没有使用 AI 摘要。",
            "preview": "PDF preview / PDF 预览",
            "item": "Knowledge-base item / 知识库条目",
        }
    if language == "English + Korean + Chinese":
        return {
            "title": "Local analysis result / 로컬 분석 결과 / 本地分析结果",
            "matched": "Relevant knowledge-base items were found automatically from the PDF. / PDF 내용과 관련된 지식베이스 항목을 자동으로 찾았습니다. / 已根据 PDF 内容自动找到相关知识库条目。",
            "local": "This is a local analysis without an OpenRouter API key. / OpenRouter API 키 없이 실행한 로컬 분석입니다. / 这是没有 OpenRouter API Key 的本地分析。",
            "details": "This result was created locally without AI summarization. / AI 요약 없이 로컬에서 만든 결과입니다. / 此结果是在本地生成的，没有使用 AI 摘要。",
            "preview": "PDF preview / PDF 미리보기 / PDF 预览",
            "item": "Knowledge-base item / 지식베이스 항목 / 知识库条目",
        }
    if language == "English":
        return {
            "title": "Local analysis result",
            "matched": "Relevant knowledge-base items were found automatically from the PDF.",
            "local": "This is a local analysis without an OpenRouter API key. PDF extraction, automatic knowledge-base search, and source inventory are available.",
            "details": "This result was created locally without AI summarization.",
            "preview": "PDF preview",
            "item": "Knowledge-base item",
        }
    if language == "Chinese":
        return {
            "title": "本地分析结果",
            "matched": "已根据 PDF 内容自动找到相关知识库条目。",
            "local": "这是没有 OpenRouter API Key 的本地分析。可以使用 PDF 提取、自动知识库搜索和来源整理功能。",
            "details": "此结果是在本地生成的，没有使用 AI 摘要。",
            "preview": "PDF 预览",
            "item": "知识库条目",
        }
    return {
        "title": "로컬 분석 결과",
        "matched": "PDF 내용과 관련된 지식베이스 항목을 자동으로 찾았습니다.",
        "local": "OpenRouter API 키 없이 실행한 로컬 분석입니다. PDF 추출, 자동 지식베이스 검색, 출처 지식베이스 생성은 사용할 수 있습니다.",
        "details": "AI 요약 없이 로컬에서 만든 결과입니다.",
        "preview": "PDF 미리보기",
        "item": "지식베이스 항목",
    }


def build_local_analysis_result(
    pdf_text: str,
    knowledge_results: list[dict],
    target_language: str,
    term_mode: str,
) -> dict:
    """Create a useful result without sending text to any AI service."""
    labels = get_local_text(target_language)
    preview = safe_string(pdf_text)[:1200]
    key_points = []
    if knowledge_results:
        key_points.append(labels["matched"])
    key_points.append(labels["local"])

    return normalize_result(
        {
            "title": labels["title"],
            "concepts": [
                safe_string(item.get("title"))
                for item in knowledge_results
                if isinstance(item, dict) and safe_string(item.get("title"))
            ][:6],
            "formulas": [],
            "key_points": key_points,
            "knowledge_references": [
                {
                    "title": safe_string(item.get("title")) or labels["item"],
                    "content": safe_string(item.get("content")),
                }
                for item in knowledge_results
                if isinstance(item, dict)
            ],
            "details": (
                f"{labels['details']}\n"
                f"target_language: {safe_string(target_language)}\n"
                f"term_mode: {safe_string(term_mode)}\n\n"
                f"[{labels['preview']}]\n{preview}"
            ),
            "glossary": [],
            "quiz": [],
        }
    )


def analyze_pdf(
    file_path: str,
    target_language: str,
    term_mode: str,
    ai_provider: str = "local",
    ollama_model: str | None = None,
) -> dict:
    """Run the full PDF study-analysis workflow without crashing Streamlit."""
    try:
        pdf_document = extract_pdf_document(file_path)
        pdf_text = pdf_document.get("text", "")
    except Exception as error:
        return normalize_result(
            {
                "error": f"PDF 처리 중 오류가 발생했습니다: {error}",
                "details": "PDF 파일을 확인한 뒤 다시 업로드해주세요.",
            }
        )

    if not safe_string(pdf_text).strip():
        return normalize_result(
            {
                "error": EMPTY_PDF_MESSAGE,
                "details": EMPTY_PDF_MESSAGE,
                "pdf_text_preview": "",
                "pdf_text_length": 0,
                "knowledge_search_count": 0,
            }
        )

    try:
        knowledge_results = search_knowledge_base(pdf_text, top_k=5)
    except Exception:
        knowledge_results = []

    local_context = {
        "pdf_text_preview": safe_string(pdf_text)[:PDF_PREVIEW_LENGTH],
        "pdf_text_length": len(safe_string(pdf_text)),
        "knowledge_search_count": len(knowledge_results),
        "auto_knowledge_results": knowledge_results,
        "pdf_pages": pdf_document.get("pages", []),
        "source_knowledge_entries": pdf_document.get("knowledge_entries", []),
        "source_knowledge_count": len(pdf_document.get("knowledge_entries", [])),
        "ocr": pdf_document.get("ocr", {}),
    }

    provider = safe_string(ai_provider).strip().lower() or "local"
    if provider not in AI_PROVIDER_LABELS:
        provider = "local"

    if provider == "local":
        analysis_result = build_local_analysis_result(
            pdf_text=pdf_text,
            knowledge_results=knowledge_results,
            target_language=target_language,
            term_mode=term_mode,
        )
    elif provider == "ollama":
        try:
            analysis_result = call_ollama_ai(
                pdf_text=pdf_text,
                knowledge_results=knowledge_results,
                target_language=target_language,
                term_mode=term_mode,
                model=ollama_model,
            )
        except Exception as error:
            analysis_result = {
                "error": f"Ollama 분석 중 오류가 발생했습니다: {error}",
                "details": AI_FAILURE_DETAILS,
            }
    else:
        try:
            analysis_result = call_openrouter_ai(
                pdf_text=pdf_text,
                knowledge_results=knowledge_results,
                target_language=target_language,
                term_mode=term_mode,
            )
        except Exception as error:
            analysis_result = {
                "error": f"OpenRouter 분석 중 오류가 발생했습니다: {error}",
                "details": AI_FAILURE_DETAILS,
            }

    normalized_result = normalize_result(analysis_result)
    normalized_result.update(local_context)
    normalized_result["ai_provider"] = provider
    normalized_result["ai_provider_label"] = AI_PROVIDER_LABELS.get(provider, "Local analysis")

    if normalized_result.get("error_code") == "openrouter_rate_limit":
        rate_limit_message = safe_string(normalized_result.get("error"))
        normalized_result = build_local_analysis_result(
            pdf_text=pdf_text,
            knowledge_results=knowledge_results,
            target_language=target_language,
            term_mode=term_mode,
        )
        normalized_result.update(local_context)
        normalized_result["ai_provider"] = "local"
        normalized_result["ai_provider_label"] = AI_PROVIDER_LABELS["local"]
        normalized_result["warning"] = (
            f"{rate_limit_message}\n\n"
            "그래도 PDF 텍스트 추출과 지식베이스 검색은 완료되어 아래 로컬 분석 결과를 표시합니다."
        )

    if provider in {"ollama", "openrouter"} and local_context["pdf_text_length"] > MAX_TEXT_LENGTH:
        truncation_warning = (
            f"PDF에서 추출된 텍스트가 {local_context['pdf_text_length']:,}자로 길어서 "
            f"AI 분석에는 앞 {MAX_TEXT_LENGTH:,}자만 사용했습니다. "
            "뒤쪽 페이지 내용은 AI 분석에 충분히 반영되지 않을 수 있습니다."
        )
        existing_warning = safe_string(normalized_result.get("warning"))
        normalized_result["warning"] = (
            f"{existing_warning}\n\n{truncation_warning}" if existing_warning else truncation_warning
        )

    if not normalized_result.get("knowledge_references") and knowledge_results:
        item_label = get_local_text(target_language)["item"]
        normalized_result["knowledge_references"] = [
            {
                "title": safe_string(item.get("title")) or item_label,
                "content": safe_string(item.get("content")),
            }
            for item in knowledge_results
            if isinstance(item, dict)
        ]

    return normalize_result(normalized_result)
