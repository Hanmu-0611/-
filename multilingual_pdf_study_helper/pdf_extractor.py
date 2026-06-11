from pathlib import Path
import re

from pypdf import PdfReader

try:
    import fitz
    import pytesseract
    from PIL import Image
except ImportError:
    fitz = None
    pytesseract = None
    Image = None


OCR_LANGUAGES = "eng+chi_sim+kor"


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


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in clean_text(text).splitlines()]
    paragraphs: list[str] = []
    buffer: list[str] = []

    for line in lines:
        if not line:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue
        buffer.append(line)

    if buffer:
        paragraphs.append(" ".join(buffer).strip())

    return [paragraph for paragraph in paragraphs if paragraph]


def ocr_page(file_path: str, page_index: int) -> tuple[str, str]:
    """OCR one PDF page. Return extracted text and an error message."""
    if fitz is None or pytesseract is None or Image is None:
        return "", "OCR 라이브러리가 설치되어 있지 않습니다."

    try:
        with fitz.open(file_path) as document:
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            return clean_text(pytesseract.image_to_string(image, lang=OCR_LANGUAGES)), ""
    except Exception as error:
        return "", str(error)


def extract_pdf_document(file_path: str, use_ocr: bool = True) -> dict:
    """Extract text, pages, and source-linked knowledge entries from a PDF."""
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

    page_items: list[dict] = []
    knowledge_entries: list[dict] = []
    ocr_pages_used = 0
    ocr_errors: list[dict] = []

    try:
        pages = reader.pages
    except Exception:
        return ""

    try:
        for page_index, page in enumerate(pages, start=1):
            try:
                text = clean_text(page.extract_text() or "")
            except Exception:
                text = ""

            extraction_method = "pdf_text"

            if use_ocr and len(text) < 20:
                ocr_text, ocr_error = ocr_page(str(path), page_index - 1)
                if ocr_text:
                    text = ocr_text
                    extraction_method = "ocr"
                    ocr_pages_used += 1
                elif ocr_error:
                    ocr_errors.append({"page": page_index, "error": ocr_error})

            paragraphs = split_paragraphs(text)
            for paragraph_index, paragraph in enumerate(paragraphs, start=1):
                if len(paragraph) < 8:
                    continue
                knowledge_entries.append(
                    {
                        "id": f"{path.name}-p{page_index}-{paragraph_index}",
                        "title": paragraph.split(".")[0][:80] or f"{page_index}페이지 {paragraph_index}문단",
                        "content": paragraph,
                        "source": {
                            "file": path.name,
                            "page": page_index,
                            "paragraph": paragraph_index,
                            "label": f"{path.name} / {page_index}페이지 / {paragraph_index}문단",
                        },
                    }
                )

            page_items.append(
                {
                    "page": page_index,
                    "text": text,
                    "char_count": len(text),
                    "paragraph_count": len(paragraphs),
                    "extraction_method": extraction_method,
                }
            )
    except Exception:
        pass

    full_text = "\n\n".join(page["text"] for page in page_items if page.get("text")).strip()
    return {
        "text": full_text,
        "pages": page_items,
        "knowledge_entries": knowledge_entries,
        "ocr": {
            "enabled": fitz is not None and pytesseract is not None and Image is not None,
            "languages": OCR_LANGUAGES,
            "pages_used": ocr_pages_used,
            "errors": ocr_errors[:10],
        },
    }


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file. Return an empty string if no text is found."""
    return extract_pdf_document(file_path).get("text", "")
