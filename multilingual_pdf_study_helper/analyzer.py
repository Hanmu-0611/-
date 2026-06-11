from ai_client import call_openrouter_ai
from knowledge_base import search_knowledge_base
from pdf_extractor import extract_pdf_document
from safe_utils import normalize_result, safe_string


EMPTY_PDF_MESSAGE = (
    "PDF에서 텍스트를 추출할 수 없습니다. "
    "이미지 기반 스캔본 PDF이거나 텍스트가 포함되지 않은 PDF일 수 있습니다."
)
AI_FAILURE_DETAILS = (
    "AI 분석을 완료하지 못했습니다. "
    "OpenRouter API 키, 모델명, 인터넷 연결 상태를 확인해주세요."
)
PDF_PREVIEW_LENGTH = 2000


def analyze_pdf(file_path: str, target_language: str, term_mode: str) -> dict:
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

    try:
        analysis_result = call_openrouter_ai(
            pdf_text=pdf_text,
            knowledge_results=knowledge_results,
            target_language=target_language,
            term_mode=term_mode,
        )
    except Exception as error:
        analysis_result = {
            "error": f"AI 분석 중 오류가 발생했습니다: {error}",
            "details": AI_FAILURE_DETAILS,
        }

    normalized_result = normalize_result(analysis_result)
    normalized_result.update(local_context)

    if "OPENROUTER_API_KEY" in safe_string(normalized_result.get("error")):
        normalized_result.update(
            {
                "title": "로컬 분석 결과",
                "warning": (
                    "OpenRouter API Key가 없어 AI 요약은 건너뛰었습니다. "
                    "PDF 텍스트 추출, 출처 지식베이스, 자동 지식베이스 검색은 정상적으로 사용할 수 있습니다."
                ),
                "error": "",
                "details": (
                    "AI 분석을 사용하려면 왼쪽 사이드바에서 OpenRouter API Key를 입력하고 저장한 뒤 다시 분석하세요. "
                    "API Key 없이도 아래의 PDF 텍스트 추출 결과와 지식베이스 검색 결과를 확인할 수 있습니다."
                ),
            }
        )

    if not normalized_result.get("knowledge_references") and knowledge_results:
        normalized_result["knowledge_references"] = [
            {
                "title": safe_string(item.get("title")) or "지식베이스 항목",
                "content": safe_string(item.get("content")),
            }
            for item in knowledge_results
            if isinstance(item, dict)
        ]

    if normalized_result.get("error"):
        normalized_result["warning"] = normalized_result.get("error")
        normalized_result["error"] = ""
        normalized_result["details"] = AI_FAILURE_DETAILS

    return normalize_result(normalized_result)
