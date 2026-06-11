from pathlib import Path
from uuid import uuid4
import json

import streamlit as st

from analyzer import analyze_pdf
from ai_client import get_current_model_info, test_openrouter_connection
from safe_utils import normalize_result, safe_list, safe_string


PROJECT_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_DIR / "uploaded_files"
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE_FILE = PROJECT_DIR / ".env.example"
DEFAULT_ENV_CONTENT = """OPENROUTER_API_KEY=여기에_API_KEY_입력
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
"""


def ensure_upload_dir() -> bool:
    """Create the upload directory if it is missing."""
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as error:
        st.error(f"업로드 폴더를 만들 수 없습니다: {error}")
        return False


def ensure_env_file() -> None:
    """Create a local .env file from .env.example for first-time users."""
    if ENV_FILE.exists():
        return

    try:
        if ENV_EXAMPLE_FILE.exists():
            env_content = ENV_EXAMPLE_FILE.read_text(encoding="utf-8")
        else:
            env_content = DEFAULT_ENV_CONTENT

        ENV_FILE.write_text(env_content, encoding="utf-8")
    except OSError:
        return


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
    show_pdf_source_inventory(safe_result)
    show_list("주요 개념", safe_result.get("concepts", []))
    show_list("공식/정의", safe_result.get("formulas", []))
    show_list("시험 핵심 내용", safe_result.get("key_points", []))
    show_knowledge_references(safe_result.get("knowledge_references", []))

    st.subheader("상세 설명")
    st.write(safe_string(safe_result.get("details")) or "상세 설명이 없습니다.")

    show_glossary(safe_result.get("glossary", []))
    show_list("복습 문제", safe_result.get("quiz", []))


def show_openrouter_status_sidebar() -> None:
    st.sidebar.header("OpenRouter 상태")

    model_info = get_current_model_info()
    model_name = safe_string(model_info.get("model"))
    st.sidebar.write(f"현재 AI 모델: {model_name}")

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


def main() -> None:
    st.set_page_config(
        page_title="다국어 PDF 지식베이스 학습 도우미 AI",
        page_icon="📘",
        layout="wide",
    )

    ensure_upload_dir()
    ensure_env_file()
    show_openrouter_status_sidebar()

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

        with st.spinner("PDF를 읽고 AI 분석을 진행하고 있습니다..."):
            try:
                result = analyze_pdf(
                    file_path=str(file_path),
                    target_language=target_language,
                    term_mode=term_mode,
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


if __name__ == "__main__":
    main()
