from pathlib import Path
from uuid import uuid4
import json

import streamlit as st

from analyzer import analyze_pdf
from ai_client import (
    get_current_model_info,
    get_ollama_model_info,
    get_openrouter_api_key,
    normalize_openrouter_api_key,
    openrouter_key_looks_valid,
    test_ollama_connection,
    test_openrouter_connection,
)
from knowledge_base import search_knowledge_base
from safe_utils import normalize_result, safe_list, safe_string


PROJECT_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_DIR / "uploaded_files"
ENV_FILE = PROJECT_DIR / ".env"
LARGE_PDF_WARNING_BYTES = 20 * 1024 * 1024
MAX_UPLOAD_SIZE_BYTES = 60 * 1024 * 1024
DEFAULT_ENV_CONTENT = """OPENROUTER_API_KEY=
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
OLLAMA_MODEL=qwen2.5:7b
"""

UI_LANGUAGE_OPTIONS = {
    "ko": "한국어",
    "en": "English",
    "zh": "中文",
}

AI_PROVIDER_OPTIONS = {
    "local": {
        "ko": "로컬 분석만 사용 (API Key 없음)",
        "en": "Local analysis only (no API key)",
        "zh": "仅使用本地分析（无需 API Key）",
    },
    "ollama": {
        "ko": "Ollama 로컬 AI 사용 (API Key 없음)",
        "en": "Use local Ollama AI (no API key)",
        "zh": "使用本地 Ollama AI（无需 API Key）",
    },
    "openrouter": {
        "ko": "OpenRouter 온라인 AI 사용",
        "en": "Use OpenRouter online AI",
        "zh": "使用 OpenRouter 在线 AI",
    },
}

TARGET_LANGUAGE_OPTIONS = {
    "Korean": {"ko": "한국어", "en": "Korean", "zh": "韩语"},
    "English": {"ko": "영어", "en": "English", "zh": "English"},
    "Chinese": {"ko": "중국어", "en": "Chinese", "zh": "中文"},
    "Korean + Chinese": {
        "ko": "한국어 + 중국어",
        "en": "Korean + Chinese",
        "zh": "韩语 + 中文",
    },
    "English + Korean": {
        "ko": "영어 + 한국어",
        "en": "English + Korean",
        "zh": "English + 韩语",
    },
    "English + Chinese": {
        "ko": "영어 + 중국어",
        "en": "English + Chinese",
        "zh": "English + 中文",
    },
    "English + Korean + Chinese": {
        "ko": "영어 + 한국어 + 중국어",
        "en": "English + Korean + Chinese",
        "zh": "English + 韩语 + 中文",
    },
}

TERM_MODE_OPTIONS = {
    "Keep English terms": {
        "ko": "영어 원어 유지",
        "en": "Keep English terms",
        "zh": "保留英文术语",
    },
    "English terms with translations": {
        "ko": "영어 + 번역 병기",
        "en": "English terms with translations",
        "zh": "英文术语 + 翻译并列",
    },
    "Translate all terms": {
        "ko": "모두 번역",
        "en": "Translate all terms",
        "zh": "全部翻译",
    },
}

TEXT = {
    "ko": {
        "site_language": "사이트 언어 / Site language / 网站语言",
        "title": "다국어 PDF 지식베이스 학습 도우미 AI",
        "intro": "외국어 강의자료 PDF를 업로드하면 PDF 내용을 추출하고, 지식베이스를 참고해 핵심 개념, 공식, 상세 설명, 복습 문제, 다국어 용어 사전을 정리합니다.",
        "upload_pdf": "PDF 파일 업로드",
        "target_language": "설명 언어 선택",
        "term_mode": "전공 용어 처리 방식",
        "start": "분석 시작",
        "upload_first": "PDF 파일을 먼저 업로드해주세요.",
        "invalid_pdf": "올바른 PDF 파일이 아닙니다. 확장자와 파일 형식을 확인해주세요.",
        "save_error": ".env 파일을 저장할 수 없습니다",
        "upload_error": "PDF 파일을 저장하는 중 오류가 발생했습니다",
        "spinner_local": "PDF를 읽고 로컬 분석을 진행하고 있습니다...",
        "spinner_ollama": "PDF를 읽고 Ollama 로컬 AI 분석을 진행하고 있습니다...",
        "spinner_openrouter": "PDF를 읽고 OpenRouter AI 분석을 진행하고 있습니다...",
        "unexpected_error": "분석 중 예상하지 못한 오류가 발생했습니다",
        "try_again": "다른 PDF로 다시 시도해주세요.",
        "ai_mode": "AI 모드",
        "analysis_method": "분석 방식 선택",
        "local_ready": "API Key 없이 로컬 분석을 사용합니다.",
        "local_caption": "PDF 추출, 출처 지식베이스, 자동 검색, 다운로드 기능을 사용할 수 있습니다.",
        "ollama_ready": "OpenRouter API Key 없이 로컬 Ollama를 사용합니다.",
        "ollama_settings": "Ollama 로컬 AI 설정",
        "ollama_model": "Ollama 모델",
        "save_ollama_model": "Ollama 모델 저장",
        "saved": "저장했습니다. 다시 분석을 실행해주세요.",
        "test_ollama": "Ollama 연결 테스트",
        "checking_ollama": "Ollama 연결을 확인하는 중입니다...",
        "ollama_success": "Ollama 연결 성공! 로컬 AI 분석을 사용할 수 있습니다.",
        "ollama_fail": "Ollama 연결에 실패했습니다.",
        "ollama_hint": "Ollama 앱을 설치/실행한 뒤 모델을 내려받아야 합니다.",
        "ollama_pull_hint": "예: ollama pull qwen2.5:7b 실행 후 사용합니다.",
        "openrouter_status": "OpenRouter 상태",
        "current_model": "현재 AI 모델",
        "api_key_set": "API Key가 설정되어 있습니다.",
        "api_key_invalid": "저장된 API Key 형식이 OpenRouter 형식이 아닙니다.",
        "api_key_missing": "API Key가 없어 AI 요약은 건너뛰고 로컬 분석만 사용합니다.",
        "api_settings": "API Key / 모델 설정",
        "openrouter_model": "OpenRouter 모델",
        "save_api_settings": "API 설정 저장",
        "api_key_hint": "OpenRouter API Key는 보통 sk-or-v1- 로 시작합니다. 다시 확인해주세요.",
        "default_model_caption": "OPENROUTER_MODEL이 비어 있거나 기본값이라 기본 무료 모델을 사용합니다.",
        "env_model_caption": ".env에 설정된 모델명을 사용합니다.",
        "test_openrouter": "OpenRouter 연결 테스트",
        "checking_openrouter": "OpenRouter 연결을 확인하는 중입니다...",
        "openrouter_success": "OpenRouter 연결 성공! AI 분석을 사용할 수 있습니다.",
        "openrouter_fail": "OpenRouter 연결에 실패했습니다. API 키, 모델명, 인터넷 연결을 확인해주세요. 무료 모델이나 OpenRouter 라우팅 상태에 따라 처음 몇 번은 실패할 수 있으니 잠시 후 여러 번 다시 시도해보세요.",
        "api_required_for_ai": "AI 분석을 완료하지 못했습니다. OpenRouter API 키를 .env 파일에 입력해주세요.",
        "result": "분석 결과",
        "ai_analysis": "AI 분석 내용",
        "local_processing": "PDF 텍스트 추출 결과",
        "extracted_length": "추출된 텍스트 길이",
        "no_pdf_text": "추출된 PDF 텍스트가 없습니다.",
        "preview": "추출된 PDF 텍스트 미리보기",
        "knowledge_status": "지식베이스 검색 상태",
        "knowledge_count": "검색된 관련 지식베이스 항목",
        "auto_knowledge": "자동 검색된 지식베이스",
        "auto_knowledge_caption": "PDF 전체 내용을 기준으로 자동 검색한 관련 지식베이스 항목입니다.",
        "no_auto_knowledge": "PDF 내용과 자동 매칭된 지식베이스 항목이 아직 없습니다.",
        "manual_search": "지식베이스 직접 검색",
        "manual_placeholder": "예: linear independence, matrix, eigenvalue",
        "manual_results": "직접 검색 결과",
        "source_inventory": "PDF 출처 지식베이스",
        "pdf_pages": "PDF 페이지",
        "source_entries": "출처 항목",
        "ocr_pages": "OCR 사용 페이지",
        "ocr_status": "OCR 상태",
        "page_status": "페이지별 추출 상태",
        "no_source_entries": "PDF에서 출처 지식베이스 항목을 만들 수 없습니다.",
        "source_search": "출처 지식베이스 검색",
        "source_placeholder": "키워드를 입력하세요",
        "showing_sources": "표시 중인 출처 항목",
        "download_md": "출처 지식베이스 Markdown 다운로드",
        "download_json": "출처 지식베이스 JSON 다운로드",
        "concepts": "주요 개념",
        "formulas": "공식/정의",
        "key_points": "시험 핵심 내용",
        "details": "상세 설명",
        "quiz": "복습 문제",
        "glossary": "다국어 용어 사전",
        "references": "지식베이스 참고 내용",
        "empty": "표시할 내용이 없습니다.",
        "reference": "참고 자료",
        "content_empty": "내용이 없습니다.",
        "keywords": "키워드",
    },
    "en": {
        "site_language": "Site language",
        "title": "Multilingual PDF Knowledge Base Study Assistant AI",
        "intro": "Upload a foreign-language lecture PDF. The app extracts the text, checks the knowledge base, and organizes key concepts, formulas, explanations, review questions, and a multilingual glossary.",
        "upload_pdf": "Upload PDF file",
        "target_language": "Explanation language",
        "term_mode": "Technical term handling",
        "start": "Start analysis",
        "upload_first": "Please upload a PDF file first.",
        "invalid_pdf": "This is not a valid PDF file. Please check the extension and file format.",
        "save_error": "Could not save the .env file",
        "upload_error": "An error occurred while saving the PDF file",
        "spinner_local": "Reading the PDF and running local analysis...",
        "spinner_ollama": "Reading the PDF and running Ollama local AI analysis...",
        "spinner_openrouter": "Reading the PDF and running OpenRouter AI analysis...",
        "unexpected_error": "An unexpected error occurred during analysis",
        "try_again": "Please try again with another PDF.",
        "ai_mode": "AI mode",
        "analysis_method": "Analysis method",
        "local_ready": "Using local analysis without an API key.",
        "local_caption": "PDF extraction, source knowledge base, automatic search, and downloads are available.",
        "ollama_ready": "Using local Ollama without an OpenRouter API key.",
        "ollama_settings": "Ollama local AI settings",
        "ollama_model": "Ollama model",
        "save_ollama_model": "Save Ollama model",
        "saved": "Saved. Please run the analysis again.",
        "test_ollama": "Test Ollama connection",
        "checking_ollama": "Checking Ollama connection...",
        "ollama_success": "Ollama connected! Local AI analysis is available.",
        "ollama_fail": "Ollama connection failed.",
        "ollama_hint": "Install/run Ollama and pull the model first.",
        "ollama_pull_hint": "Example: run ollama pull qwen2.5:7b before using it.",
        "openrouter_status": "OpenRouter status",
        "current_model": "Current AI model",
        "api_key_set": "API key is configured.",
        "api_key_invalid": "The saved API key is not in the OpenRouter format.",
        "api_key_missing": "No API key found. AI summary will be skipped and local analysis will be used.",
        "api_settings": "API key / model settings",
        "openrouter_model": "OpenRouter model",
        "save_api_settings": "Save API settings",
        "api_key_hint": "OpenRouter API keys usually start with sk-or-v1-. Please check again.",
        "default_model_caption": "OPENROUTER_MODEL is empty or default, so the default free model is used.",
        "env_model_caption": "Using the model name set in .env.",
        "test_openrouter": "Test OpenRouter connection",
        "checking_openrouter": "Checking OpenRouter connection...",
        "openrouter_success": "OpenRouter connected! AI analysis is available.",
        "openrouter_fail": "OpenRouter connection failed. Check the API key, model name, and internet connection. Free models or OpenRouter routing can fail on the first few attempts, so wait a moment and try several times.",
        "api_required_for_ai": "AI analysis could not be completed. Enter an OpenRouter API key in the .env file.",
        "result": "Analysis result",
        "ai_analysis": "AI analysis",
        "local_processing": "Extracted PDF text",
        "extracted_length": "Extracted text length",
        "no_pdf_text": "No PDF text was extracted.",
        "preview": "Extracted PDF text preview",
        "knowledge_status": "Knowledge base search status",
        "knowledge_count": "Relevant knowledge base items found",
        "auto_knowledge": "Automatically searched knowledge base",
        "auto_knowledge_caption": "Related knowledge base items found from the full PDF text.",
        "no_auto_knowledge": "No knowledge base items were automatically matched yet.",
        "manual_search": "Search knowledge base manually",
        "manual_placeholder": "e.g. linear independence, matrix, eigenvalue",
        "manual_results": "Manual search results",
        "source_inventory": "PDF source knowledge base",
        "pdf_pages": "PDF pages",
        "source_entries": "Source entries",
        "ocr_pages": "OCR pages used",
        "ocr_status": "OCR status",
        "page_status": "Page extraction status",
        "no_source_entries": "No source knowledge base entries could be created from the PDF.",
        "source_search": "Search source knowledge base",
        "source_placeholder": "Enter a keyword",
        "showing_sources": "Displayed source entries",
        "download_md": "Download source knowledge base Markdown",
        "download_json": "Download source knowledge base JSON",
        "concepts": "Key concepts",
        "formulas": "Formulas & definitions",
        "key_points": "Exam key points",
        "details": "Detailed explanation",
        "quiz": "Review questions",
        "glossary": "Multilingual glossary",
        "references": "Knowledge base references",
        "empty": "No content to display.",
        "reference": "Reference",
        "content_empty": "No content.",
        "keywords": "Keywords",
    },
    "zh": {
        "site_language": "网站语言",
        "title": "多语言 PDF 知识库学习助手 AI",
        "intro": "上传外语课程 PDF 后，应用会提取文本，参考知识库整理核心概念、公式、详细说明、复习题和多语言术语表。",
        "upload_pdf": "上传 PDF 文件",
        "target_language": "说明语言",
        "term_mode": "专业术语处理方式",
        "start": "开始分析",
        "upload_first": "请先上传 PDF 文件。",
        "invalid_pdf": "这不是有效的 PDF 文件。请检查扩展名和文件格式。",
        "save_error": "无法保存 .env 文件",
        "upload_error": "保存 PDF 文件时发生错误",
        "spinner_local": "正在读取 PDF 并进行本地分析...",
        "spinner_ollama": "正在读取 PDF 并进行 Ollama 本地 AI 分析...",
        "spinner_openrouter": "正在读取 PDF 并进行 OpenRouter AI 分析...",
        "unexpected_error": "分析过程中发生了意外错误",
        "try_again": "请尝试使用其他 PDF。",
        "ai_mode": "AI 模式",
        "analysis_method": "选择分析方式",
        "local_ready": "无需 API Key，使用本地分析。",
        "local_caption": "可以使用 PDF 提取、来源知识库、自动搜索和下载功能。",
        "ollama_ready": "无需 OpenRouter API Key，使用本地 Ollama。",
        "ollama_settings": "Ollama 本地 AI 设置",
        "ollama_model": "Ollama 模型",
        "save_ollama_model": "保存 Ollama 模型",
        "saved": "已保存。请重新运行分析。",
        "test_ollama": "测试 Ollama 连接",
        "checking_ollama": "正在检查 Ollama 连接...",
        "ollama_success": "Ollama 连接成功！可以使用本地 AI 分析。",
        "ollama_fail": "Ollama 连接失败。",
        "ollama_hint": "请先安装/运行 Ollama 并下载模型。",
        "ollama_pull_hint": "例如：运行 ollama pull qwen2.5:7b 后再使用。",
        "openrouter_status": "OpenRouter 状态",
        "current_model": "当前 AI 模型",
        "api_key_set": "API Key 已设置。",
        "api_key_invalid": "保存的 API Key 不是 OpenRouter 格式。",
        "api_key_missing": "没有 API Key，将跳过 AI 摘要并只使用本地分析。",
        "api_settings": "API Key / 模型设置",
        "openrouter_model": "OpenRouter 模型",
        "save_api_settings": "保存 API 设置",
        "api_key_hint": "OpenRouter API Key 通常以 sk-or-v1- 开头。请重新确认。",
        "default_model_caption": "OPENROUTER_MODEL 为空或为默认值，因此使用默认免费模型。",
        "env_model_caption": "使用 .env 中设置的模型名称。",
        "test_openrouter": "测试 OpenRouter 连接",
        "checking_openrouter": "正在检查 OpenRouter 连接...",
        "openrouter_success": "OpenRouter 连接成功！可以使用 AI 分析。",
        "openrouter_fail": "OpenRouter 连接失败。请检查 API Key、模型名称和网络连接。免费模型或 OpenRouter 路由有时前几次会失败，请稍等后多试几次。",
        "api_required_for_ai": "AI 分析未能完成。请在 .env 文件中输入 OpenRouter API Key。",
        "result": "分析结果",
        "ai_analysis": "AI 分析内容",
        "local_processing": "PDF 文本提取结果",
        "extracted_length": "提取的文本长度",
        "no_pdf_text": "没有提取到 PDF 文本。",
        "preview": "提取的 PDF 文本预览",
        "knowledge_status": "知识库搜索状态",
        "knowledge_count": "找到的相关知识库条目",
        "auto_knowledge": "自动搜索的知识库",
        "auto_knowledge_caption": "根据 PDF 全文自动搜索到的相关知识库条目。",
        "no_auto_knowledge": "尚未自动匹配到知识库条目。",
        "manual_search": "手动搜索知识库",
        "manual_placeholder": "例如：linear independence, matrix, eigenvalue",
        "manual_results": "手动搜索结果",
        "source_inventory": "PDF 来源知识库",
        "pdf_pages": "PDF 页数",
        "source_entries": "来源条目",
        "ocr_pages": "使用 OCR 的页数",
        "ocr_status": "OCR 状态",
        "page_status": "按页提取状态",
        "no_source_entries": "无法从 PDF 创建来源知识库条目。",
        "source_search": "搜索来源知识库",
        "source_placeholder": "请输入关键词",
        "showing_sources": "正在显示的来源条目",
        "download_md": "下载来源知识库 Markdown",
        "download_json": "下载来源知识库 JSON",
        "concepts": "核心概念",
        "formulas": "公式/定义",
        "key_points": "考试重点",
        "details": "详细说明",
        "quiz": "复习题",
        "glossary": "多语言术语表",
        "references": "知识库参考内容",
        "empty": "没有可显示的内容。",
        "reference": "参考资料",
        "content_empty": "没有内容。",
        "keywords": "关键词",
    },
}


def t(ui_language: str, key: str) -> str:
    return TEXT.get(ui_language, TEXT["ko"]).get(key, TEXT["ko"].get(key, key))


def ensure_upload_dir(ui_language: str) -> bool:
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as error:
        st.error(f"{t(ui_language, 'upload_error')}: {error}")
        return False


def ensure_env_file() -> None:
    if ENV_FILE.exists():
        return

    try:
        ENV_FILE.write_text(DEFAULT_ENV_CONTENT, encoding="utf-8")
    except OSError:
        return


def save_openrouter_settings(api_key: str, model_name: str, ui_language: str) -> bool:
    normalized_key = normalize_openrouter_api_key(api_key)

    try:
        ENV_FILE.write_text(
            "\n".join(
                [
                    f"OPENROUTER_API_KEY={normalized_key}",
                    f"OPENROUTER_MODEL={safe_string(model_name).strip()}",
                    f"OLLAMA_MODEL={get_ollama_model_info().get('model')}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return True
    except OSError as error:
        st.sidebar.error(f"{t(ui_language, 'save_error')}: {error}")
        return False


def save_ollama_settings(model_name: str, ui_language: str) -> bool:
    openrouter_key = get_openrouter_api_key()
    openrouter_model = get_current_model_info().get("model")
    ollama_model = safe_string(model_name).strip() or get_ollama_model_info().get("model")

    try:
        ENV_FILE.write_text(
            "\n".join(
                [
                    f"OPENROUTER_API_KEY={openrouter_key}",
                    f"OPENROUTER_MODEL={openrouter_model}",
                    f"OLLAMA_MODEL={ollama_model}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return True
    except OSError as error:
        st.sidebar.error(f"{t(ui_language, 'save_error')}: {error}")
        return False


def get_uploaded_file_size(uploaded_file) -> int:
    size = getattr(uploaded_file, "size", None)
    if isinstance(size, int) and size >= 0:
        return size

    try:
        current_position = uploaded_file.tell()
        uploaded_file.seek(0, 2)
        size = uploaded_file.tell()
        uploaded_file.seek(current_position)
        return int(size)
    except Exception:
        return 0


def format_file_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def get_large_pdf_warning(ui_language: str, file_size: int) -> str:
    size_text = format_file_size(file_size)
    ai_limit_text = "20,000"
    if ui_language == "en":
        return (
            f"This PDF is large ({size_text}). Text extraction can still run, but AI analysis uses only "
            f"the first {ai_limit_text} extracted characters, so later pages may not be reflected."
        )
    if ui_language == "zh":
        return (
            f"这个 PDF 较大（{size_text}）。仍然可以提取文本，但 AI 分析只会使用前 "
            f"{ai_limit_text} 个提取字符，因此后面的页面可能不会反映在分析中。"
        )
    return (
        f"PDF 파일이 큽니다({size_text}). 텍스트 추출은 진행할 수 있지만 AI 분석에는 "
        f"추출 텍스트 앞 {ai_limit_text}자만 사용되므로 뒤쪽 페이지 내용은 반영되지 않을 수 있습니다."
    )


def get_too_large_pdf_error(ui_language: str, file_size: int) -> str:
    size_text = format_file_size(file_size)
    limit_text = format_file_size(MAX_UPLOAD_SIZE_BYTES)
    if ui_language == "en":
        return (
            f"This PDF is too large ({size_text}). Please use a PDF under {limit_text} "
            "or split/compress the file before uploading."
        )
    if ui_language == "zh":
        return (
            f"这个 PDF 太大（{size_text}）。请上传小于 {limit_text} 的 PDF，"
            "或先拆分/压缩文件。"
        )
    return (
        f"PDF 파일이 너무 큽니다({size_text}). {limit_text} 이하의 PDF를 사용하거나 "
        "파일을 나누거나 압축한 뒤 업로드해주세요."
    )


def uploaded_file_is_pdf(uploaded_file) -> bool:
    if uploaded_file is None:
        return False

    file_name = safe_string(getattr(uploaded_file, "name", ""))
    if Path(file_name).suffix.lower() != ".pdf":
        return False

    try:
        current_position = uploaded_file.tell()
        uploaded_file.seek(0)
        header = uploaded_file.read(5)
        uploaded_file.seek(current_position)
    except Exception:
        return False

    return header == b"%PDF-"


def save_uploaded_file(uploaded_file, ui_language: str) -> Path | None:
    if not ensure_upload_dir(ui_language):
        return None

    safe_name = Path(safe_string(uploaded_file.name)).name or "uploaded.pdf"
    file_path = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"

    try:
        uploaded_file.seek(0)
        with file_path.open("wb") as output_file:
            output_file.write(uploaded_file.getbuffer())
    except Exception as error:
        st.error(f"{t(ui_language, 'upload_error')}: {error}")
        return None

    return file_path


def show_list(ui_language: str, title_key: str, value) -> None:
    st.subheader(t(ui_language, title_key))
    items = [safe_string(item) for item in safe_list(value) if safe_string(item)]

    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.info(t(ui_language, "empty"))


def show_knowledge_references(ui_language: str, value) -> None:
    st.subheader(t(ui_language, "references"))
    references = safe_list(value)

    if not references:
        st.info(t(ui_language, "empty"))
        return

    for reference in references:
        if isinstance(reference, dict):
            title = safe_string(reference.get("title")) or t(ui_language, "reference")
            content = safe_string(reference.get("content"))
        else:
            title = t(ui_language, "reference")
            content = safe_string(reference)

        with st.expander(title):
            st.write(content or t(ui_language, "content_empty"))


def show_auto_knowledge_search(ui_language: str, result: dict) -> None:
    st.subheader(t(ui_language, "auto_knowledge"))

    auto_results = safe_list(result.get("auto_knowledge_results"))
    if auto_results:
        st.caption(t(ui_language, "auto_knowledge_caption"))
        for item in auto_results:
            if not isinstance(item, dict):
                continue
            title = safe_string(item.get("title")) or t(ui_language, "reference")
            content = safe_string(item.get("content"))
            keywords = ", ".join(
                safe_string(keyword)
                for keyword in safe_list(item.get("keywords"))
                if safe_string(keyword)
            )
            with st.expander(title):
                if keywords:
                    st.caption(f"{t(ui_language, 'keywords')}: {keywords}")
                st.write(content or t(ui_language, "content_empty"))
    else:
        st.info(t(ui_language, "no_auto_knowledge"))

    manual_query = st.text_input(
        t(ui_language, "manual_search"),
        placeholder=t(ui_language, "manual_placeholder"),
    )
    if manual_query:
        manual_results = search_knowledge_base(manual_query, top_k=8)
        st.write(f"{t(ui_language, 'manual_results')}: {len(manual_results)}")
        for item in manual_results:
            if not isinstance(item, dict):
                continue
            with st.expander(safe_string(item.get("title")) or t(ui_language, "reference")):
                st.write(safe_string(item.get("content")) or t(ui_language, "content_empty"))


def build_source_markdown(entries) -> str:
    lines = ["# PDF Source Knowledge Base", ""]
    for index, entry in enumerate(safe_list(entries), start=1):
        if not isinstance(entry, dict):
            continue

        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        lines.extend(
            [
                f"## {index}. {safe_string(entry.get('title')) or 'Knowledge item'}",
                f"- Source: {safe_string(source.get('label'))}",
                "",
                safe_string(entry.get("content")),
                "",
            ]
        )
    return "\n".join(lines).strip()


def show_pdf_source_inventory(ui_language: str, result: dict) -> None:
    st.subheader(t(ui_language, "source_inventory"))

    entries = safe_list(result.get("source_knowledge_entries"))
    pages = safe_list(result.get("pdf_pages"))
    ocr_info = result.get("ocr") if isinstance(result.get("ocr"), dict) else {}

    col1, col2, col3 = st.columns(3)
    col1.metric(t(ui_language, "pdf_pages"), len(pages))
    col2.metric(t(ui_language, "source_entries"), len(entries))
    col3.metric(t(ui_language, "ocr_pages"), ocr_info.get("pages_used", 0))

    if ocr_info.get("errors"):
        with st.expander(t(ui_language, "ocr_status")):
            for item in safe_list(ocr_info.get("errors")):
                if isinstance(item, dict):
                    st.caption(f"{item.get('page')}: {item.get('error')}")

    if pages:
        with st.expander(t(ui_language, "page_status")):
            st.table(
                [
                    {
                        "Page": page.get("page"),
                        "Method": page.get("extraction_method"),
                        "Characters": page.get("char_count"),
                        "Paragraphs": page.get("paragraph_count"),
                    }
                    for page in pages
                    if isinstance(page, dict)
                ]
            )

    if not entries:
        st.info(t(ui_language, "no_source_entries"))
        return

    keyword = st.text_input(
        t(ui_language, "source_search"),
        placeholder=t(ui_language, "source_placeholder"),
    )
    keyword_lower = safe_string(keyword).lower().strip()
    filtered_entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        searchable = f"{entry.get('title', '')} {entry.get('content', '')}".lower()
        if keyword_lower and keyword_lower not in searchable:
            continue
        filtered_entries.append(entry)

    st.write(f"{t(ui_language, 'showing_sources')}: {len(filtered_entries)}")
    for entry in filtered_entries[:30]:
        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        with st.expander(safe_string(source.get("label")) or safe_string(entry.get("title"))):
            st.write(safe_string(entry.get("content")))

    st.download_button(
        t(ui_language, "download_md"),
        data=build_source_markdown(entries),
        file_name="pdf_source_knowledge_base.md",
        mime="text/markdown",
    )
    st.download_button(
        t(ui_language, "download_json"),
        data=json.dumps(entries, ensure_ascii=False, indent=2),
        file_name="pdf_source_knowledge_base.json",
        mime="application/json",
    )


def show_glossary(ui_language: str, value) -> None:
    st.subheader(t(ui_language, "glossary"))
    glossary = safe_list(value)

    if not glossary:
        st.info(t(ui_language, "empty"))
        return

    rows = []
    for term in glossary:
        if isinstance(term, dict):
            rows.append(
                {
                    "English": safe_string(term.get("english")),
                    "Korean": safe_string(term.get("korean")),
                    "Chinese": safe_string(term.get("chinese")),
                    "Explanation": safe_string(term.get("explanation")),
                }
            )
        else:
            rows.append(
                {
                    "English": safe_string(term),
                    "Korean": "",
                    "Chinese": "",
                    "Explanation": "",
                }
            )

    st.table(rows)


def show_local_processing_result(ui_language: str, result: dict) -> None:
    st.subheader(t(ui_language, "local_processing"))
    text_length = result.get("pdf_text_length", 0)
    text_preview = safe_string(result.get("pdf_text_preview"))

    if text_length:
        st.write(f"{t(ui_language, 'extracted_length')}: {text_length}")
    else:
        st.info(t(ui_language, "no_pdf_text"))

    if text_preview:
        with st.expander(t(ui_language, "preview")):
            st.write(text_preview)

    st.subheader(t(ui_language, "knowledge_status"))
    search_count = result.get("knowledge_search_count", 0)
    st.write(f"{t(ui_language, 'knowledge_count')}: {search_count}")


def show_analysis_result(ui_language: str, result: dict) -> None:
    safe_result = normalize_result(result)

    if safe_result.get("warning"):
        st.warning(safe_result.get("warning", ""))

    st.header(safe_result.get("title") or t(ui_language, "result"))
    show_local_processing_result(ui_language, safe_result)
    show_auto_knowledge_search(ui_language, safe_result)
    show_pdf_source_inventory(ui_language, safe_result)

    st.markdown(
        """
        <div style="border-top: 2px dashed #b8c0cc; margin: 2rem 0 1.25rem 0;"></div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader(t(ui_language, "ai_analysis"))

    show_list(ui_language, "concepts", safe_result.get("concepts", []))
    show_list(ui_language, "formulas", safe_result.get("formulas", []))
    show_list(ui_language, "key_points", safe_result.get("key_points", []))
    show_knowledge_references(ui_language, safe_result.get("knowledge_references", []))

    st.subheader(t(ui_language, "details"))
    st.write(safe_string(safe_result.get("details")) or t(ui_language, "empty"))

    show_glossary(ui_language, safe_result.get("glossary", []))
    show_list(ui_language, "quiz", safe_result.get("quiz", []))


def show_ai_settings_sidebar(ui_language: str) -> tuple[str, str]:
    st.sidebar.header(t(ui_language, "ai_mode"))

    selected_provider = st.sidebar.selectbox(
        t(ui_language, "analysis_method"),
        list(AI_PROVIDER_OPTIONS.keys()),
        format_func=lambda key: AI_PROVIDER_OPTIONS[key][ui_language],
    )

    if selected_provider == "local":
        st.sidebar.success(t(ui_language, "local_ready"))
        st.sidebar.caption(t(ui_language, "local_caption"))
        return selected_provider, ""

    if selected_provider == "ollama":
        ollama_info = get_ollama_model_info()
        ollama_model = safe_string(ollama_info.get("model"))
        st.sidebar.success(t(ui_language, "ollama_ready"))

        with st.sidebar.expander(t(ui_language, "ollama_settings"), expanded=True):
            ollama_model_input = st.text_input(
                t(ui_language, "ollama_model"),
                value=ollama_model,
                placeholder="qwen2.5:7b",
            )
            if st.button(t(ui_language, "save_ollama_model")):
                if save_ollama_settings(ollama_model_input, ui_language):
                    st.sidebar.success(t(ui_language, "saved"))

            if st.button(t(ui_language, "test_ollama")):
                with st.sidebar.spinner(t(ui_language, "checking_ollama")):
                    try:
                        test_result = test_ollama_connection(ollama_model_input)
                    except Exception as error:
                        test_result = {"success": False, "message": safe_string(error)}

                if test_result.get("success"):
                    st.sidebar.success(t(ui_language, "ollama_success"))
                else:
                    st.sidebar.error(t(ui_language, "ollama_fail"))
                    st.sidebar.caption(t(ui_language, "ollama_hint"))
                    if test_result.get("message"):
                        st.sidebar.caption(safe_string(test_result.get("message")))

        st.sidebar.caption(t(ui_language, "ollama_pull_hint"))
        return selected_provider, safe_string(ollama_model_input).strip() or ollama_model

    st.sidebar.header(t(ui_language, "openrouter_status"))

    model_info = get_current_model_info()
    model_name = safe_string(model_info.get("model"))
    current_key = get_openrouter_api_key()
    st.sidebar.write(f"{t(ui_language, 'current_model')}: {model_name}")

    if current_key:
        if openrouter_key_looks_valid(current_key):
            st.sidebar.success(t(ui_language, "api_key_set"))
        else:
            st.sidebar.error(t(ui_language, "api_key_invalid"))
    else:
        st.sidebar.warning(t(ui_language, "api_key_missing"))

    with st.sidebar.expander(t(ui_language, "api_settings")):
        api_key_input = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-v1-...",
        )
        model_input = st.text_input(
            t(ui_language, "openrouter_model"),
            value=model_name,
        )
        if st.button(t(ui_language, "save_api_settings")):
            key_to_save = api_key_input.strip() or current_key
            if key_to_save and not openrouter_key_looks_valid(normalize_openrouter_api_key(key_to_save)):
                st.sidebar.error(t(ui_language, "api_key_hint"))
                return selected_provider, ""
            if save_openrouter_settings(key_to_save, model_input, ui_language):
                st.sidebar.success(t(ui_language, "saved"))

    if model_info.get("uses_default"):
        st.sidebar.caption(t(ui_language, "default_model_caption"))
    else:
        st.sidebar.caption(t(ui_language, "env_model_caption"))

    if st.sidebar.button(t(ui_language, "test_openrouter")):
        with st.sidebar.spinner(t(ui_language, "checking_openrouter")):
            try:
                test_result = test_openrouter_connection()
            except Exception as error:
                test_result = {"success": False, "message": safe_string(error)}

        if test_result.get("success"):
            st.sidebar.success(t(ui_language, "openrouter_success"))
        else:
            st.sidebar.error(t(ui_language, "openrouter_fail"))
            if test_result.get("message"):
                st.sidebar.caption(safe_string(test_result.get("message")))

    return selected_provider, ""


def main() -> None:
    st.set_page_config(
        page_title="Multilingual PDF Study Helper AI",
        page_icon="📘",
        layout="wide",
    )

    ensure_env_file()

    ui_language = st.selectbox(
        TEXT["ko"]["site_language"],
        list(UI_LANGUAGE_OPTIONS.keys()),
        format_func=lambda key: UI_LANGUAGE_OPTIONS[key],
    )

    ai_provider, ollama_model = show_ai_settings_sidebar(ui_language)

    st.title(t(ui_language, "title"))
    st.write(t(ui_language, "intro"))

    uploaded_file = st.file_uploader(t(ui_language, "upload_pdf"), type=["pdf"])

    target_language = st.selectbox(
        t(ui_language, "target_language"),
        list(TARGET_LANGUAGE_OPTIONS.keys()),
        format_func=lambda key: TARGET_LANGUAGE_OPTIONS[key][ui_language],
    )

    term_mode = st.selectbox(
        t(ui_language, "term_mode"),
        list(TERM_MODE_OPTIONS.keys()),
        format_func=lambda key: TERM_MODE_OPTIONS[key][ui_language],
    )

    if st.button(t(ui_language, "start"), type="primary"):
        if uploaded_file is None:
            st.warning(t(ui_language, "upload_first"))
            return

        uploaded_file_size = get_uploaded_file_size(uploaded_file)
        if uploaded_file_size > MAX_UPLOAD_SIZE_BYTES:
            st.error(get_too_large_pdf_error(ui_language, uploaded_file_size))
            return
        if uploaded_file_size > LARGE_PDF_WARNING_BYTES:
            st.warning(get_large_pdf_warning(ui_language, uploaded_file_size))

        if not uploaded_file_is_pdf(uploaded_file):
            st.error(t(ui_language, "invalid_pdf"))
            return

        file_path = save_uploaded_file(uploaded_file, ui_language)
        if file_path is None:
            return

        if ai_provider == "local":
            spinner_text = t(ui_language, "spinner_local")
        elif ai_provider == "ollama":
            spinner_text = t(ui_language, "spinner_ollama")
        else:
            spinner_text = t(ui_language, "spinner_openrouter")

        with st.spinner(spinner_text):
            try:
                result = analyze_pdf(
                    file_path=str(file_path),
                    target_language=target_language,
                    term_mode=term_mode,
                    ai_provider=ai_provider,
                    ollama_model=ollama_model,
                )
            except Exception as error:
                result = {
                    "error": f"{t(ui_language, 'unexpected_error')}: {error}",
                    "details": t(ui_language, "try_again"),
                }

        safe_result = normalize_result(result)

        if safe_result.get("error"):
            st.error(safe_result.get("error", t(ui_language, "api_required_for_ai")))

        show_analysis_result(ui_language, safe_result)


if __name__ == "__main__":
    main()
