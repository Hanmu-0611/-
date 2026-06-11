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
DEFAULT_ENV_CONTENT = """OPENROUTER_API_KEY=
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
OLLAMA_MODEL=qwen2.5:7b
"""
AI_PROVIDER_OPTIONS = {
    "로컬 분석만 사용 (API Key 없음)": "local",
    "Ollama 로컬 AI 사용 (API Key 없음)": "ollama",
    "OpenRouter 온라인 AI 사용": "openrouter",
}


CLEAN_AI_PROVIDER_OPTIONS = {
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

UI_LANGUAGE_OPTIONS = {
    "ko": "한국어",
    "en": "English",
    "zh": "中文",
}

TARGET_LANGUAGE_OPTIONS = {
    "English": {"ko": "English", "en": "English", "zh": "English"},
    "Korean": {"ko": "한국어", "en": "Korean", "zh": "韩语"},
    "Chinese": {"ko": "中文", "en": "Chinese", "zh": "中文"},
    "English + Korean": {
        "ko": "English + 한국어",
        "en": "English + Korean",
        "zh": "English + 韩语",
    },
    "English + Chinese": {
        "ko": "English + 中文",
        "en": "English + Chinese",
        "zh": "English + 中文",
    },
    "Korean + Chinese": {
        "ko": "한국어 + 中文",
        "en": "Korean + Chinese",
        "zh": "韩语 + 中文",
    },
    "English + Korean + Chinese": {
        "ko": "English + 한국어 + 中文",
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

UI_TEXT = {
    "ko": {
        "ui_language": "사이트 언어",
        "title": "다국어 PDF 지식베이스 학습 도우미 AI",
        "intro": "외국어 강의자료 PDF를 업로드하면 AI가 PDF 내용을 자동으로 추출하고, 지식베이스를 참고해 핵심 개념, 공식, 상세 설명, 복습 문제, 다국어 용어 사전을 정리해줍니다.",
        "upload_pdf": "PDF 파일 업로드",
        "target_language": "설명 언어 선택",
        "target_language_help": "중국어는 언어 선택 목록에서 中文으로 표시됩니다.",
        "term_mode": "전공 용어 처리 방식 선택",
        "start": "분석 시작",
        "upload_first": "PDF 파일을 먼저 업로드해주세요.",
        "invalid_pdf": "올바른 PDF 파일이 아닙니다. 확장자와 파일 형식을 확인해주세요.",
        "spinner_local": "PDF를 읽고 로컬 분석을 진행하고 있습니다...",
        "spinner_ollama": "PDF를 읽고 Ollama 로컬 AI 분석을 진행하고 있습니다...",
        "spinner_openrouter": "PDF를 읽고 OpenRouter AI 분석을 진행하고 있습니다...",
        "unexpected_error": "분석 중 예상하지 못한 오류가 발생했습니다",
        "try_again": "작업은 계속 실행됩니다. 다른 PDF로 다시 시도해주세요.",
        "analysis_error": "분석 중 오류가 발생했습니다.",
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
        "openrouter_fail": "OpenRouter 연결에 실패했습니다. API 키, 모델명, 인터넷 연결을 확인해주세요.",
    },
    "en": {
        "ui_language": "Site language",
        "title": "Multilingual PDF Knowledge Base Study Assistant AI",
        "intro": "Upload a foreign-language lecture PDF, and the app extracts text, checks the knowledge base, and organizes key concepts, formulas, explanations, review questions, and a multilingual glossary.",
        "upload_pdf": "Upload PDF file",
        "target_language": "Explanation language",
        "target_language_help": "Chinese is displayed as 中文 in the language options.",
        "term_mode": "Technical term handling",
        "start": "Start analysis",
        "upload_first": "Please upload a PDF file first.",
        "invalid_pdf": "This is not a valid PDF file. Please check the extension and file format.",
        "spinner_local": "Reading the PDF and running local analysis...",
        "spinner_ollama": "Reading the PDF and running Ollama local AI analysis...",
        "spinner_openrouter": "Reading the PDF and running OpenRouter AI analysis...",
        "unexpected_error": "An unexpected error occurred during analysis",
        "try_again": "The app is still running. Please try again with another PDF.",
        "analysis_error": "An error occurred during analysis.",
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
        "openrouter_fail": "OpenRouter connection failed. Check the API key, model name, and internet connection.",
    },
    "zh": {
        "ui_language": "网站语言",
        "title": "多语言 PDF 知识库学习助手 AI",
        "intro": "上传外语课程 PDF 后，应用会自动提取内容，参考知识库整理核心概念、公式、详细说明、复习题和多语言术语表。",
        "upload_pdf": "上传 PDF 文件",
        "target_language": "说明语言",
        "target_language_help": "语言选项中的中文会显示为 中文。",
        "term_mode": "专业术语处理方式",
        "start": "开始分析",
        "upload_first": "请先上传 PDF 文件。",
        "invalid_pdf": "这不是有效的 PDF 文件。请检查扩展名和文件格式。",
        "spinner_local": "正在读取 PDF 并进行本地分析...",
        "spinner_ollama": "正在读取 PDF 并进行 Ollama 本地 AI 分析...",
        "spinner_openrouter": "正在读取 PDF 并进行 OpenRouter AI 分析...",
        "unexpected_error": "分析过程中发生了意外错误",
        "try_again": "应用会继续运行。请尝试使用其他 PDF。",
        "analysis_error": "分析过程中发生错误。",
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
        "openrouter_fail": "OpenRouter 连接失败。请检查 API Key、模型名称和网络连接。",
    },
}


def get_ui_text(ui_language: str, key: str) -> str:
    return UI_TEXT.get(ui_language, UI_TEXT["ko"]).get(key, UI_TEXT["ko"].get(key, key))


def ensure_upload_dir() -> bool:
    """Create the upload directory if it is missing."""
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as error:
        st.error(f"업로드 폴더를 만들 수 없습니다: {error}")
        return False


def ensure_env_file() -> None:
    """Create the default .env file if it is missing."""
    if ENV_FILE.exists():
        return

    try:
        ENV_FILE.write_text(DEFAULT_ENV_CONTENT, encoding="utf-8")
    except OSError:
        return


def save_openrouter_settings(api_key: str, model_name: str) -> bool:
    """Save OpenRouter settings to the local .env file."""
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
        st.sidebar.error(f".env 파일을 저장할 수 없습니다: {error}")
        return False


def save_ollama_settings(model_name: str) -> bool:
    """Save the preferred Ollama model without requiring an API key."""
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
        st.sidebar.error(f".env 파일을 저장할 수 없습니다: {error}")
        return False


def uploaded_file_is_pdf(uploaded_file) -> bool:
    """Validate the uploaded file name and PDF header."""
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


def save_uploaded_file(uploaded_file) -> Path | None:
    """Save the uploaded PDF and return its local path."""
    if not ensure_upload_dir():
        return None

    safe_name = Path(safe_string(uploaded_file.name)).name or "uploaded.pdf"
    file_path = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"

    try:
        uploaded_file.seek(0)
        with file_path.open("wb") as output_file:
            output_file.write(uploaded_file.getbuffer())
    except Exception as error:
        st.error(f"PDF 파일을 저장하는 중 오류가 발생했습니다: {error}")
        return None

    return file_path


def show_list(title: str, value) -> None:
    st.subheader(title)
    items = [safe_string(item) for item in safe_list(value) if safe_string(item)]

    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.info("표시할 내용이 없습니다.")


def show_knowledge_references(value) -> None:
    st.subheader("지식베이스 참고 내용")
    references = safe_list(value)

    if not references:
        st.info("관련 지식베이스 항목을 찾지 못했거나 참고 자료가 비어 있습니다.")
        return

    for reference in references:
        if isinstance(reference, dict):
            title = safe_string(reference.get("title")) or "참고 자료"
            content = safe_string(reference.get("content"))
        else:
            title = "참고 자료"
            content = safe_string(reference)

        with st.expander(title):
            st.write(content or "내용이 없습니다.")


def show_auto_knowledge_search(result: dict) -> None:
    st.subheader("자동 검색된 지식베이스")

    auto_results = safe_list(result.get("auto_knowledge_results"))
    if auto_results:
        st.caption("PDF 전체 내용을 기준으로 자동 검색한 관련 지식베이스 항목입니다.")
        for item in auto_results:
            if not isinstance(item, dict):
                continue
            title = safe_string(item.get("title")) or "지식베이스 항목"
            content = safe_string(item.get("content"))
            keywords = ", ".join(safe_string(keyword) for keyword in safe_list(item.get("keywords")) if safe_string(keyword))
            with st.expander(title):
                if keywords:
                    st.caption(f"키워드: {keywords}")
                st.write(content or "내용이 없습니다.")
    else:
        st.info("PDF 내용과 자동 매칭된 지식베이스 항목이 아직 없습니다.")

    manual_query = st.text_input(
        "지식베이스 직접 검색",
        placeholder="예: linear independence, matrix, eigenvalue, 선형독립",
    )
    if manual_query:
        manual_results = search_knowledge_base(manual_query, top_k=8)
        st.write(f"직접 검색 결과: {len(manual_results)}개")
        for item in manual_results:
            if not isinstance(item, dict):
                continue
            with st.expander(safe_string(item.get("title")) or "검색 결과"):
                st.write(safe_string(item.get("content")) or "내용이 없습니다.")


def build_source_markdown(entries) -> str:
    lines = ["# PDF 출처 지식베이스", ""]
    for index, entry in enumerate(safe_list(entries), start=1):
        if not isinstance(entry, dict):
            continue

        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        lines.extend(
            [
                f"## {index}. {safe_string(entry.get('title')) or '지식 항목'}",
                f"- 출처: {safe_string(source.get('label'))}",
                "",
                safe_string(entry.get("content")),
                "",
            ]
        )
    return "\n".join(lines).strip()


def show_pdf_source_inventory(result: dict) -> None:
    st.subheader("PDF 출처 지식베이스")

    entries = safe_list(result.get("source_knowledge_entries"))
    pages = safe_list(result.get("pdf_pages"))
    ocr_info = result.get("ocr") if isinstance(result.get("ocr"), dict) else {}

    col1, col2, col3 = st.columns(3)
    col1.metric("PDF 페이지", len(pages))
    col2.metric("출처 항목", len(entries))
    col3.metric("OCR 사용 페이지", ocr_info.get("pages_used", 0))

    if ocr_info.get("errors"):
        st.warning(
            "일부 페이지에서 PDF 내부 글자 인코딩이 깨졌지만 OCR을 실행하지 못했습니다. "
            "로컬 컴퓨터에 Tesseract OCR을 설치하면 숫자/공식 영역을 더 잘 복구할 수 있습니다."
        )

    if ocr_info.get("errors"):
        with st.expander("OCR 상태"):
            for item in safe_list(ocr_info.get("errors")):
                if isinstance(item, dict):
                    st.caption(f"{item.get('page')}페이지: {item.get('error')}")

    if pages:
        with st.expander("페이지별 추출 상태"):
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
        st.info("PDF에서 출처 지식베이스 항목을 만들 수 없습니다.")
        return

    keyword = st.text_input("출처 지식베이스 검색", placeholder="키워드를 입력하세요")
    keyword_lower = safe_string(keyword).lower().strip()
    filtered_entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        searchable = f"{entry.get('title', '')} {entry.get('content', '')}".lower()
        if keyword_lower and keyword_lower not in searchable:
            continue
        filtered_entries.append(entry)

    st.write(f"표시 중인 출처 항목: {len(filtered_entries)}개")
    for entry in filtered_entries[:30]:
        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        with st.expander(safe_string(source.get("label")) or safe_string(entry.get("title"))):
            st.write(safe_string(entry.get("content")))

    source_markdown = build_source_markdown(entries)
    st.download_button(
        "출처 지식베이스 Markdown 다운로드",
        data=source_markdown,
        file_name="pdf_source_knowledge_base.md",
        mime="text/markdown",
    )
    st.download_button(
        "출처 지식베이스 JSON 다운로드",
        data=json.dumps(entries, ensure_ascii=False, indent=2),
        file_name="pdf_source_knowledge_base.json",
        mime="application/json",
    )


def show_glossary(value) -> None:
    st.subheader("다국어 용어 사전")
    glossary = safe_list(value)

    if not glossary:
        st.info("용어 사전이 비어 있습니다.")
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


def show_local_processing_result(result: dict) -> None:
    st.subheader("PDF 텍스트 추출 결과")
    text_length = result.get("pdf_text_length", 0)
    text_preview = safe_string(result.get("pdf_text_preview"))

    if text_length:
        st.write(f"추출된 텍스트 길이: {text_length}자")
    else:
        st.info("추출된 PDF 텍스트가 없습니다.")

    if text_preview:
        with st.expander("추출된 PDF 텍스트 미리보기"):
            st.write(text_preview)

    st.subheader("지식베이스 검색 상태")
    search_count = result.get("knowledge_search_count", 0)
    st.write(f"검색된 관련 지식베이스 항목 수: {search_count}개")


def show_analysis_result(result: dict) -> None:
    safe_result = normalize_result(result)

    if safe_result.get("warning"):
        st.warning(safe_result.get("warning", ""))

    st.header(safe_result.get("title", "분석 결과"))
    show_local_processing_result(safe_result)
    show_auto_knowledge_search(safe_result)
    show_pdf_source_inventory(safe_result)
    show_list("주요 개념", safe_result.get("concepts", []))
    show_list("공식/정의", safe_result.get("formulas", []))
    show_list("시험 핵심 내용", safe_result.get("key_points", []))
    show_knowledge_references(safe_result.get("knowledge_references", []))

    st.subheader("상세 설명")
    st.write(safe_string(safe_result.get("details")) or "상세 설명이 없습니다.")

    show_glossary(safe_result.get("glossary", []))
    show_list("복습 문제", safe_result.get("quiz", []))


def show_ai_settings_sidebar() -> tuple[str, str]:
    st.sidebar.header("AI 모드")

    selected_label = st.sidebar.selectbox(
        "분석 방식 선택",
        list(AI_PROVIDER_OPTIONS.keys()),
    )
    ai_provider = AI_PROVIDER_OPTIONS.get(selected_label, "local")

    if ai_provider == "local":
        st.sidebar.success("API Key 없이 로컬 분석을 사용합니다.")
        st.sidebar.caption("PDF 추출, 출처 지식베이스, 자동 검색, 다운로드 기능을 사용할 수 있습니다.")
        return ai_provider, ""

    if ai_provider == "ollama":
        ollama_info = get_ollama_model_info()
        ollama_model = safe_string(ollama_info.get("model"))
        st.sidebar.success("OpenRouter API Key 없이 로컬 Ollama를 사용합니다.")

        with st.sidebar.expander("Ollama 로컬 AI 설정", expanded=True):
            ollama_model_input = st.text_input(
                "Ollama 모델",
                value=ollama_model,
                placeholder="qwen2.5:7b",
            )
            if st.button("Ollama 모델 저장"):
                if save_ollama_settings(ollama_model_input):
                    st.sidebar.success("저장했습니다. 다시 분석을 실행해주세요.")

            if st.button("Ollama 연결 테스트"):
                with st.sidebar.spinner("Ollama 연결을 확인하는 중입니다..."):
                    try:
                        test_result = test_ollama_connection(ollama_model_input)
                    except Exception as error:
                        test_result = {
                            "success": False,
                            "message": safe_string(error),
                        }

                if test_result.get("success"):
                    st.sidebar.success("Ollama 연결 성공! 로컬 AI 분석을 사용할 수 있습니다.")
                else:
                    st.sidebar.error("Ollama 연결에 실패했습니다.")
                    st.sidebar.caption("Ollama 앱을 설치/실행한 뒤 모델을 내려받아야 합니다.")
                    if test_result.get("message"):
                        st.sidebar.caption(safe_string(test_result.get("message")))

        st.sidebar.caption("예: ollama pull qwen2.5:7b 실행 후 사용합니다.")
        return ai_provider, safe_string(ollama_model_input).strip() or ollama_model

    st.sidebar.header("OpenRouter 상태")

    model_info = get_current_model_info()
    model_name = safe_string(model_info.get("model"))
    current_key = get_openrouter_api_key()
    st.sidebar.write(f"현재 AI 모델: {model_name}")

    if current_key:
        if openrouter_key_looks_valid(current_key):
            st.sidebar.success("API Key가 설정되어 있습니다.")
        else:
            st.sidebar.error("저장된 API Key 형식이 OpenRouter 형식이 아닙니다.")
    else:
        st.sidebar.warning("API Key가 없어 AI 요약은 건너뛰고 로컬 분석만 사용합니다.")

    with st.sidebar.expander("API Key / 모델 설정"):
        api_key_input = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-...",
        )
        model_input = st.text_input(
            "OpenRouter 모델",
            value=model_name,
        )
        if st.button("API 설정 저장"):
            key_to_save = api_key_input.strip() or current_key
            if key_to_save and not openrouter_key_looks_valid(normalize_openrouter_api_key(key_to_save)):
                st.sidebar.error("OpenRouter API Key는 보통 sk-or-v1- 로 시작합니다. 다시 확인해주세요.")
                return
            if save_openrouter_settings(key_to_save, model_input):
                st.sidebar.success("저장했습니다. 다시 분석을 실행해주세요.")

    if model_info.get("uses_default"):
        st.sidebar.caption("OPENROUTER_MODEL이 비어 있거나 기본값이라 기본 무료 모델을 사용합니다.")
    else:
        st.sidebar.caption(".env에 설정된 모델명을 사용합니다.")

    if st.sidebar.button("OpenRouter 연결 테스트"):
        with st.sidebar.spinner("OpenRouter 연결을 확인하는 중입니다..."):
            try:
                test_result = test_openrouter_connection()
            except Exception as error:
                test_result = {
                    "success": False,
                    "message": safe_string(error),
                }

        if test_result.get("success"):
            st.sidebar.success("OpenRouter 연결 성공! AI 분석을 사용할 수 있습니다.")
        else:
            st.sidebar.error("OpenRouter 연결에 실패했습니다. API 키, 모델명, 인터넷 연결을 확인해주세요.")
            if test_result.get("message"):
                st.sidebar.caption(safe_string(test_result.get("message")))

    return ai_provider, ""


def main() -> None:
    st.set_page_config(
        page_title="다국어 PDF 지식베이스 학습 도우미 AI",
        page_icon="📘",
        layout="wide",
    )

    ensure_upload_dir()
    ensure_env_file()
    ai_provider, ollama_model = show_ai_settings_sidebar()

    st.title("다국어 PDF 지식베이스 학습 도우미 AI")
    st.write(
        "외국어 강의자료 PDF를 업로드하면 AI가 PDF 내용을 자동으로 추출하고, "
        "지식베이스를 참고하여 핵심 개념, 공식, 상세 설명, 복습 문제, "
        "다국어 용어 사전을 정리해주는 로컬 웹앱입니다."
    )

    uploaded_file = st.file_uploader("PDF 파일 업로드", type=["pdf"])

    target_language = st.selectbox(
        "설명 언어 선택",
        [
            "English",
            "한국어",
            "중국어",
            "English + 한국어",
            "English + 중국어",
            "한국어 + 중국어",
            "English + 한국어 + 중국어",
        ],
    )
    st.info("中文对照已开启：翻译和整理结果会默认包含中文说明。")

    term_mode = st.selectbox(
        "전공 용어 처리 방식 선택",
        ["영어 원어 유지", "영어 + 번역 병기", "모두 번역"],
    )

    if st.button("분석 시작", type="primary"):
        if uploaded_file is None:
            st.warning("PDF 파일을 먼저 업로드해주세요.")
            return

        if not uploaded_file_is_pdf(uploaded_file):
            st.error("올바른 PDF 파일이 아닙니다. 확장자와 파일 형식을 확인해주세요.")
            return

        file_path = save_uploaded_file(uploaded_file)
        if file_path is None:
            return

        if ai_provider == "local":
            spinner_text = "PDF를 읽고 로컬 분석을 진행하고 있습니다..."
        elif ai_provider == "ollama":
            spinner_text = "PDF를 읽고 Ollama 로컬 AI 분석을 진행하고 있습니다..."
        else:
            spinner_text = "PDF를 읽고 OpenRouter AI 분석을 진행하고 있습니다..."

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
                    "error": f"분석 중 예상하지 못한 오류가 발생했습니다: {error}",
                    "details": "앱은 계속 실행됩니다. 다른 PDF로 다시 시도해주세요.",
                }

        safe_result = normalize_result(result)

        if safe_result.get("error"):
            st.error(safe_result.get("error", "분석 중 오류가 발생했습니다."))

        show_analysis_result(safe_result)


def show_ai_settings_sidebar_i18n(ui_language: str) -> tuple[str, str]:
    text = lambda key: get_ui_text(ui_language, key)

    st.sidebar.header(text("ai_mode"))

    selected_provider = st.sidebar.selectbox(
        text("analysis_method"),
        list(CLEAN_AI_PROVIDER_OPTIONS.keys()),
        format_func=lambda key: CLEAN_AI_PROVIDER_OPTIONS[key][ui_language],
    )

    if selected_provider == "local":
        st.sidebar.success(text("local_ready"))
        st.sidebar.caption(text("local_caption"))
        return selected_provider, ""

    if selected_provider == "ollama":
        ollama_info = get_ollama_model_info()
        ollama_model = safe_string(ollama_info.get("model"))
        st.sidebar.success(text("ollama_ready"))

        with st.sidebar.expander(text("ollama_settings"), expanded=True):
            ollama_model_input = st.text_input(
                text("ollama_model"),
                value=ollama_model,
                placeholder="qwen2.5:7b",
            )
            if st.button(text("save_ollama_model")):
                if save_ollama_settings(ollama_model_input):
                    st.sidebar.success(text("saved"))

            if st.button(text("test_ollama")):
                with st.sidebar.spinner(text("checking_ollama")):
                    try:
                        test_result = test_ollama_connection(ollama_model_input)
                    except Exception as error:
                        test_result = {
                            "success": False,
                            "message": safe_string(error),
                        }

                if test_result.get("success"):
                    st.sidebar.success(text("ollama_success"))
                else:
                    st.sidebar.error(text("ollama_fail"))
                    st.sidebar.caption(text("ollama_hint"))
                    if test_result.get("message"):
                        st.sidebar.caption(safe_string(test_result.get("message")))

        st.sidebar.caption(text("ollama_pull_hint"))
        return selected_provider, safe_string(ollama_model_input).strip() or ollama_model

    st.sidebar.header(text("openrouter_status"))

    model_info = get_current_model_info()
    model_name = safe_string(model_info.get("model"))
    current_key = get_openrouter_api_key()
    st.sidebar.write(f"{text('current_model')}: {model_name}")

    if current_key:
        if openrouter_key_looks_valid(current_key):
            st.sidebar.success(text("api_key_set"))
        else:
            st.sidebar.error(text("api_key_invalid"))
    else:
        st.sidebar.warning(text("api_key_missing"))

    with st.sidebar.expander(text("api_settings")):
        api_key_input = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-...",
        )
        model_input = st.text_input(
            text("openrouter_model"),
            value=model_name,
        )
        if st.button(text("save_api_settings")):
            key_to_save = api_key_input.strip() or current_key
            if key_to_save and not openrouter_key_looks_valid(normalize_openrouter_api_key(key_to_save)):
                st.sidebar.error(text("api_key_hint"))
                return selected_provider, ""
            if save_openrouter_settings(key_to_save, model_input):
                st.sidebar.success(text("saved"))

    if model_info.get("uses_default"):
        st.sidebar.caption(text("default_model_caption"))
    else:
        st.sidebar.caption(text("env_model_caption"))

    if st.sidebar.button(text("test_openrouter")):
        with st.sidebar.spinner(text("checking_openrouter")):
            try:
                test_result = test_openrouter_connection()
            except Exception as error:
                test_result = {
                    "success": False,
                    "message": safe_string(error),
                }

        if test_result.get("success"):
            st.sidebar.success(text("openrouter_success"))
        else:
            st.sidebar.error(text("openrouter_fail"))
            if test_result.get("message"):
                st.sidebar.caption(safe_string(test_result.get("message")))

    return selected_provider, ""


def main() -> None:
    st.set_page_config(
        page_title="Multilingual PDF Study Helper AI",
        page_icon="📘",
        layout="wide",
    )

    ensure_upload_dir()
    ensure_env_file()

    ui_language = st.selectbox(
        "사이트 언어 / Site language / 网站语言",
        list(UI_LANGUAGE_OPTIONS.keys()),
        format_func=lambda key: UI_LANGUAGE_OPTIONS[key],
    )
    st.session_state["ui_language"] = ui_language
    text = lambda key: get_ui_text(ui_language, key)

    ai_provider, ollama_model = show_ai_settings_sidebar_i18n(ui_language)

    st.title(text("title"))
    st.write(text("intro"))

    uploaded_file = st.file_uploader(text("upload_pdf"), type=["pdf"])

    target_language = st.selectbox(
        text("target_language"),
        list(TARGET_LANGUAGE_OPTIONS.keys()),
        format_func=lambda key: TARGET_LANGUAGE_OPTIONS[key][ui_language],
    )
    st.info(text("target_language_help"))

    term_mode = st.selectbox(
        text("term_mode"),
        list(TERM_MODE_OPTIONS.keys()),
        format_func=lambda key: TERM_MODE_OPTIONS[key][ui_language],
    )

    if st.button(text("start"), type="primary"):
        if uploaded_file is None:
            st.warning(text("upload_first"))
            return

        if not uploaded_file_is_pdf(uploaded_file):
            st.error(text("invalid_pdf"))
            return

        file_path = save_uploaded_file(uploaded_file)
        if file_path is None:
            return

        if ai_provider == "local":
            spinner_text = text("spinner_local")
        elif ai_provider == "ollama":
            spinner_text = text("spinner_ollama")
        else:
            spinner_text = text("spinner_openrouter")

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
                    "error": f"{text('unexpected_error')}: {error}",
                    "details": text("try_again"),
                }

        safe_result = normalize_result(result)

        if safe_result.get("error"):
            st.error(safe_result.get("error", text("analysis_error")))

        show_analysis_result(safe_result)


if __name__ == "__main__":
    main()
