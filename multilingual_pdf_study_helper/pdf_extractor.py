from pathlib import Path

from pypdf import PdfReader


def is_probably_pdf(file_path: str) -> bool:
    """Check extension and file header before pypdf tries to parse the file."""
    path = Path(file_path)

    if path.suffix.lower() != ".pdf":
        return False

    try:
        with path.open("rb") as pdf_file:
            header = pdf_file.read(5)
    except OSError:
        return False

    return header == b"%PDF-"


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file. Return an empty string if no text is found."""
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError("PDF 파일을 찾을 수 없습니다.")

    if not is_probably_pdf(str(path)):
        raise ValueError("PDF 형식의 파일이 아닙니다. 올바른 PDF 파일을 업로드해주세요.")

    try:
        reader = PdfReader(str(path))
    except Exception as error:
        raise ValueError(f"PDF 파일을 읽을 수 없습니다. 파일이 손상되었을 수 있습니다. ({error})")

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            return ""

    page_texts: list[str] = []

    try:
        pages = reader.pages
    except Exception:
        return ""

    try:
        for page in pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""

            text = text.strip()
            if text:
                page_texts.append(text)
    except Exception:
        return "\n\n".join(page_texts).strip()

    return "\n\n".join(page_texts).strip()
