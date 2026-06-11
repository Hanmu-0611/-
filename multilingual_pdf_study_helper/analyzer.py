from ai_client import call_ollama_ai, call_openrouter_ai
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
    "local": "로컬 분석",
    "ollama": "Ollama 로컬 AI",
    "openrouter": "OpenRouter 온라인 AI",
}


def build_local_analysis_result(
    pdf_text: str,
    knowledge_results: list[dict],
    target_language: str,
    term_mode: str,
) -> dict:
    """Create a useful result without sending text to any AI service."""
    preview = safe_string(pdf_text)[:1200]
    key_points = []
    if knowledge_results:
        key_points.append(
            "PDF 내용과 관련된 지식베이스 항목을 자동으로 찾았습니다. "
            "AI 요약 없이도 아래 참고 항목과 PDF 출처 지식베이스를 확인할 수 있습니다."
        )
    key_points.append(
        "OpenRouter API 키 없이 실행한 로컬 분석입니다. PDF 텍스트 추출, "
        "자동 지식베이스 검색, 출처 지식베이스 생성은 사용할 수 있습니다."
    )

    return normalize_result(
        {
            "title": "로컬 분석 결과",
            "concepts": [
                safe_string(item.get("title"))
                for item in knowledge_results
                if isinstance(item, dict) and safe_string(item.get("title"))
            ][:6],
            "formulas": [],
            "key_points": key_points,
            "knowledge_references": [
                {
                    "title": safe_string(item.get("title")) or "지식베이스 항목",
                    "content": safe_string(item.get("content")),
                }
                for item in knowledge_results
                if isinstance(item, dict)
            ],
            "details": (
                "API 키 없이 실행한 로컬 분석입니다. "
                f"설명 언어 설정: {safe_string(target_language)}, "
                f"용어 처리 설정: {safe_string(term_mode)}.\n\n"
                f"[PDF 미리보기]\n{preview}"
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
    normalized_result["ai_provider_label"] = AI_PROVIDER_LABELS.get(provider, "로컬 분석")

    if not normalized_result.get("knowledge_references") and knowledge_results:
        normalized_result["knowledge_references"] = [
            {
                "title": safe_string(item.get("title")) or "지식베이스 항목",
                "content": safe_string(item.get("content")),
            }
            for item in knowledge_results
            if isinstance(item, dict)
        ]

    return normalize_result(normalized_result)
