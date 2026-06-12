from pathlib import Path
from io import BytesIO
import os
import re

from pypdf import PdfReader
from safe_utils import add_multilingual_spacing

try:
    import fitz
    import pytesseract
    from PIL import Image
except ImportError:
    fitz = None
    pytesseract = None
    Image = None

USE_MACOS_VISION_OCR = os.getenv("USE_MACOS_VISION_OCR", "").lower() in {"1", "true", "yes"}

try:
    from ocrmac import ocrmac as mac_ocr
except ImportError:
    mac_ocr = None


OCR_LANGUAGES = "eng+chi_sim+kor"
GARBLE_CHARS = "�ØßÕÜÛÐÑÃÂÅÄ€Þ"
MATH_SYMBOL_REPLACEMENTS = {
    "−": "-",
    "–": "-",
    "—": "-",
    "×": "*",
    "÷": "/",
    "∗": "*",
    "≤": "<=",
    "≥": ">=",
    "≠": "!=",
    "≈": "~",
    "∑": "Σ",
    "∏": "Π",
    "√": "sqrt",
    "∞": "infinity",
    "π": "pi",
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "λ": "lambda",
    "μ": "mu",
    "σ": "sigma",
    "²": "^2",
    "³": "^3",
    "¹": "^1",
    "⁰": "^0",
    "⁴": "^4",
    "⁵": "^5",
    "⁶": "^6",
    "⁷": "^7",
    "⁸": "^8",
    "⁹": "^9",
    "₀": "_0",
    "₁": "_1",
    "₂": "_2",
    "₃": "_3",
    "₄": "_4",
    "₅": "_5",
    "₆": "_6",
    "₇": "_7",
    "₈": "_8",
    "₉": "_9",
}


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


def normalize_math_text(text: str) -> str:
    """Normalize common PDF math glyphs without deleting numeric meaning."""
    normalized = text or ""
    for source, target in MATH_SYMBOL_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)

    normalized = re.sub(r"(?<=\d)\s*([+\-*/=<>])\s*(?=\d)", r" \1 ", normalized)
    normalized = re.sub(r"(?<=[A-Za-z])\s*\^\s*(?=\d)", "^", normalized)
    normalized = re.sub(r"(?<=[A-Za-z])\s*_\s*(?=\d)", "_", normalized)
    normalized = re.sub(r"([A-Za-z])\s+([A-Za-z])(?=\s*[=+\-*/])", r"\1\2", normalized)
    normalized = re.sub(r"(?<=\d)\s*,\s*(?=\d{3}\b)", ",", normalized)
    normalized = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", normalized)
    return normalized


def garble_ratio(text: str) -> float:
    if not text:
        return 0.0
    garbled = sum(1 for char in text if char in GARBLE_CHARS)
    return garbled / max(len(text), 1)


def is_garbled_text(text: str) -> bool:
    if not text:
        return False
    if text.count("�") >= 2:
        return True
    if len(re.findall(r"[ØÕÜÛß]{2,}", text)) >= 2:
        return True
    return garble_ratio(text) >= 0.08


def clean_garbled_line(line: str) -> str:
    line = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", line)

    if not is_garbled_text(line):
        line = re.sub(r"[ØÕÜÛßÐÑÃÂÅÄ€Þ�][A-Za-z0-9ØÕÜÛßÐÑÃÂÅÄ€Þ�_<>|=+\-*/^]*", "[변수 인코딩 깨짐]", line)
        return re.sub(r"\s+", " ", line).strip()

    readable = re.sub(r"[ØÕÜÛßÐÑÃÂÅÄ€Þ�]+[A-Za-z0-9ØÕÜÛßÐÑÃÂÅÄ€Þ�_<>|=+\-*/^ ]*", " ", line)
    readable = re.sub(r"\s+", " ", readable).strip(" -•·")

    if len(readable) >= 8 and garble_ratio(readable) < 0.03:
        return f"{readable} [공식/숫자 인코딩 깨짐 - OCR 필요]"

    return "[공식/숫자 인코딩 깨짐 - OCR 필요]"


def remove_garbled_lines(text: str) -> str:
    cleaned_lines = []
    for line in (text or "").splitlines():
        cleaned_lines.append(clean_garbled_line(line))
    return "\n".join(cleaned_lines)


def clean_text(text: str) -> str:
    text = normalize_math_text(text)
    text = re.sub(r"[ \t]+\n", "\n", text or "")
    text = re.sub(r"\n\s*([+\-*/=<>])\s*\n", r" \1 ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = remove_garbled_lines(text)
    return add_multilingual_spacing(text).strip()


def is_formula_like(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    math_chars = sum(1 for char in line if char.isdigit() or char in "=+-*/^_<>[](){}ΣΠ")
    return math_chars >= 3 and math_chars / max(len(line), 1) >= 0.22


def text_quality_score(text: str) -> int:
    """Prefer text with more readable numbers/formulas and fewer replacement boxes."""
    cleaned = safe_len_text(text)
    if not cleaned:
        return 0
    score = len(cleaned)
    score += len(re.findall(r"\d+(?:[.,]\d+)?", cleaned)) * 8
    score += len(re.findall(r"[=+\-*/^_<>]|sqrt|lambda|sigma|alpha|beta", cleaned)) * 4
    score -= cleaned.count("�") * 30
    score -= cleaned.count("□") * 20
    score -= len(re.findall(r"[ØÕÜÛß]{2,}", cleaned)) * 25
    score -= cleaned.count("인코딩 깨짐") * 80
    return score


def safe_len_text(text: str) -> str:
    return clean_text(text or "")


def extract_text_with_fitz(file_path: str, page_index: int) -> str:
    if fitz is None:
        return ""
    try:
        with fitz.open(file_path) as document:
            return clean_text(document.load_page(page_index).get_text("text") or "")
    except Exception:
        return ""


def choose_best_page_text(pypdf_text: str, fitz_text: str) -> str:
    if text_quality_score(fitz_text) > text_quality_score(pypdf_text) + 20:
        return fitz_text
    return pypdf_text


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
        if is_formula_like(line):
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            paragraphs.append(line)
            continue
        buffer.append(line)

    if buffer:
        paragraphs.append(" ".join(buffer).strip())

    return [paragraph for paragraph in paragraphs if paragraph]


def ocr_page(file_path: str, page_index: int) -> tuple[str, str]:
    """OCR one PDF page. Return extracted text and an error message."""
    if fitz is None or Image is None:
        return "", "OCR 이미지 처리 라이브러리가 설치되어 있지 않습니다."

    try:
        with fitz.open(file_path) as document:
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

        if pytesseract is not None:
            try:
                pytesseract.get_tesseract_version()
                text = pytesseract.image_to_string(image, lang=OCR_LANGUAGES)
                if text.strip():
                    return clean_text(text), ""
            except Exception:
                pass

        if USE_MACOS_VISION_OCR and mac_ocr is not None:
            mac_errors = []
            for framework in ("vision", "livetext"):
                try:
                    results = mac_ocr.OCR(
                        image,
                        framework=framework,
                        language_preference=["ko-KR", "zh-Hans", "en-US"],
                        detail=True,
                    ).recognize()
                    text = "\n".join(item[0] for item in results if item and item[0])
                    if text.strip():
                        return clean_text(text), ""
                except Exception as error:
                    mac_errors.append(f"{framework}: {error}")

            try:
                results = mac_ocr.OCR(
                    image,
                    language_preference=["ko-KR", "zh-Hans", "en-US"],
                    detail=True,
                ).recognize()
                text = "\n".join(item[0] for item in results if item and item[0])
                if text.strip():
                    return clean_text(text), ""
            except Exception as error:
                mac_errors.append(f"default: {error}")

            if mac_errors:
                return "", "macOS OCR 오류: " + " | ".join(mac_errors)

        return "", "OCR 엔진을 찾을 수 없습니다. Tesseract OCR 설치가 필요합니다."
    except Exception as error:
        return "", str(error)


def ocr_pil_image(image) -> tuple[str, str]:
    """OCR one PIL image. Return extracted text and an error message."""
    if Image is None:
        return "", "OCR 이미지 처리 라이브러리가 설치되어 있지 않습니다."

    if pytesseract is not None:
        try:
            pytesseract.get_tesseract_version()
            text = pytesseract.image_to_string(image, lang=OCR_LANGUAGES)
            if text.strip():
                return clean_text(text), ""
        except Exception:
            pass

    if USE_MACOS_VISION_OCR and mac_ocr is not None:
        mac_errors = []
        for framework in ("vision", "livetext"):
            try:
                results = mac_ocr.OCR(
                    image,
                    framework=framework,
                    language_preference=["ko-KR", "zh-Hans", "en-US"],
                    detail=True,
                ).recognize()
                text = "\n".join(item[0] for item in results if item and item[0])
                if text.strip():
                    return clean_text(text), ""
            except Exception as error:
                mac_errors.append(f"{framework}: {error}")

        if mac_errors:
            return "", "macOS OCR 오류: " + " | ".join(mac_errors)

    return "", "OCR 엔진을 찾을 수 없습니다. Tesseract OCR 설치가 필요합니다."


def ocr_embedded_images(file_path: str, page_index: int) -> tuple[list[str], list[str]]:
    """Extract and OCR images embedded in a PDF page."""
    if fitz is None or Image is None:
        return [], ["OCR 이미지 처리 라이브러리가 설치되어 있지 않습니다."]

    image_texts: list[str] = []
    image_errors: list[str] = []

    try:
        with fitz.open(file_path) as document:
            page = document.load_page(page_index)
            image_refs = page.get_images(full=True)
            for image_number, image_ref in enumerate(image_refs, start=1):
                xref = image_ref[0]
                try:
                    image_info = document.extract_image(xref)
                    image_bytes = image_info.get("image")
                    if not image_bytes:
                        continue
                    image = Image.open(BytesIO(image_bytes)).convert("RGB")
                    width, height = image.size
                    if width < 80 or height < 40:
                        continue
                    image_text, image_error = ocr_pil_image(image)
                    if image_text:
                        image_texts.append(f"[Image {image_number} OCR]\n{image_text}")
                    elif image_error:
                        image_errors.append(f"image {image_number}: {image_error}")
                except Exception as error:
                    image_errors.append(f"image {image_number}: {error}")
    except Exception as error:
        image_errors.append(str(error))

    return image_texts, image_errors


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
    ocr_images_used = 0
    ocr_errors: list[dict] = []

    try:
        pages = reader.pages
    except Exception:
        return ""

    try:
        for page_index, page in enumerate(pages, start=1):
            try:
                pypdf_text = clean_text(page.extract_text() or "")
            except Exception:
                pypdf_text = ""

            fitz_text = extract_text_with_fitz(str(path), page_index - 1)
            text = choose_best_page_text(pypdf_text, fitz_text)

            extraction_method = "pdf_text"
            needs_ocr = len(text) < 20 or is_garbled_text(pypdf_text) or is_garbled_text(fitz_text) or "인코딩 깨짐" in text

            if use_ocr and needs_ocr:
                ocr_text, ocr_error = ocr_page(str(path), page_index - 1)
                if ocr_text:
                    text = ocr_text
                    extraction_method = "ocr"
                    ocr_pages_used += 1
                elif ocr_error:
                    ocr_errors.append({"page": page_index, "error": ocr_error})
                    if "인코딩 깨짐" not in text:
                        text = remove_garbled_lines(text)

            if use_ocr and extraction_method != "ocr":
                image_texts, image_errors = ocr_embedded_images(str(path), page_index - 1)
                if image_texts:
                    text = "\n\n".join([text, *image_texts]).strip()
                    extraction_method = (
                        "pdf_text+image_ocr"
                        if extraction_method == "pdf_text"
                        else f"{extraction_method}+image_ocr"
                    )
                    ocr_images_used += len(image_texts)
                for image_error in image_errors[:3]:
                    ocr_errors.append({"page": page_index, "error": image_error})

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
            "enabled": fitz is not None and Image is not None and pytesseract is not None,
            "languages": OCR_LANGUAGES,
            "macos_vision_available": USE_MACOS_VISION_OCR and mac_ocr is not None,
            "pages_used": ocr_pages_used,
            "images_used": ocr_images_used,
            "errors": ocr_errors[:10],
        },
    }


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file. Return an empty string if no text is found."""
    return extract_pdf_document(file_path).get("text", "")
