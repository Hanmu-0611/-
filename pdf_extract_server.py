#!/usr/bin/env python3
"""
Small PDF extraction app and API for connecting an existing website.

Run:
  python3 pdf_extract_server.py

Endpoint:
  POST /api/extract-pdf
  multipart/form-data field name: file
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from pypdf import PdfReader

try:
    import fitz
    import pytesseract
    from PIL import Image
except ImportError:
    fitz = None
    pytesseract = None
    Image = None


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
UPLOAD_DIR = Path(tempfile.gettempdir()) / "pdf_extract_uploads"
KNOWLEDGE_BASE_PATH = Path(__file__).with_name("knowledge_base.jsonl")
OCR_LANGUAGES = os.environ.get("OCR_LANGUAGES", "eng+chi_sim+kor")

APP_HTML = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PDF 自动整理知识库</title>
    <style>
      body {
        margin: 0;
        font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
        background: #f5f7f8;
        color: #1f2937;
      }

      main {
        max-width: 980px;
        margin: 38px auto;
        padding: 0 20px;
      }

      h1 {
        margin: 0 0 18px;
        font-size: 28px;
        line-height: 1.25;
      }

      .panel {
        background: #fff;
        border: 1px solid #d8dde6;
        border-radius: 8px;
        padding: 20px;
      }

      .controls,
      .search {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
      }

      .search {
        margin: 14px 0;
      }

      input,
      button,
      textarea,
      select {
        font: inherit;
      }

      input[type="search"] {
        flex: 1;
        min-width: 220px;
        padding: 9px 10px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
      }

      select {
        padding: 8px 10px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: #fff;
      }

      button {
        padding: 9px 14px;
        border: 0;
        border-radius: 6px;
        background: #14532d;
        color: #fff;
        cursor: pointer;
      }

      button:disabled {
        opacity: 0.55;
        cursor: wait;
      }

      .meta {
        min-height: 22px;
        margin: 14px 0;
        color: #4b5563;
      }

      textarea {
        box-sizing: border-box;
        width: 100%;
        min-height: 520px;
        padding: 14px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        resize: vertical;
        line-height: 1.55;
        white-space: pre-wrap;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>PDF 自动整理知识库</h1>
      <section class="panel">
        <div class="controls">
          <input id="pdfInput" type="file" accept="application/pdf,.pdf" />
          <select id="viewMode">
            <option value="organized">整理结果</option>
            <option value="knowledge">知识库出处</option>
            <option value="text">原始文本</option>
            <option value="ocr">OCR 状态</option>
            <option value="json">JSON 数据</option>
          </select>
          <button id="extractButton">提交并整理</button>
        </div>
        <div id="meta" class="meta"></div>
        <div class="search">
          <input id="searchInput" type="search" placeholder="搜索知识库，例如：合同、日期、摘要、关键词" />
          <button id="searchButton">查询出处</button>
        </div>
        <textarea id="pdfText" placeholder="用户提交 PDF 后，整理结果会显示在这里"></textarea>
      </section>
    </main>

    <script>
      const input = document.querySelector("#pdfInput");
      const button = document.querySelector("#extractButton");
      const output = document.querySelector("#pdfText");
      const meta = document.querySelector("#meta");
      const viewMode = document.querySelector("#viewMode");
      const searchInput = document.querySelector("#searchInput");
      const searchButton = document.querySelector("#searchButton");
      let latestResult = null;

      function formatKnowledgeEntries(entries) {
        if (!entries || entries.length === 0) {
          return "暂无知识库内容。请先上传 PDF，或换一个关键词查询。";
        }

        return entries
          .map((entry, index) => {
            return [
              `${index + 1}. ${entry.title}`,
              `出处：${entry.source.label}`,
              `类型：${entry.kind}`,
              `内容：${entry.content}`,
            ].join("\\n");
          })
          .join("\\n\\n---\\n\\n");
      }

      function renderResult() {
        if (!latestResult) return;
        if (viewMode.value === "knowledge") {
          output.value = formatKnowledgeEntries(latestResult.knowledge_base.entries);
          return;
        }
        if (viewMode.value === "text") {
          output.value = latestResult.text;
          return;
        }
        if (viewMode.value === "ocr") {
          output.value = JSON.stringify(latestResult.ocr, null, 2);
          return;
        }
        if (viewMode.value === "json") {
          output.value = JSON.stringify(latestResult, null, 2);
          return;
        }
        output.value = latestResult.organized.markdown;
      }

      async function extractPdfFromFile(file) {
        if (!file) throw new Error("请选择一个 PDF 文件");
        if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
          throw new Error("只能上传 PDF 文件");
        }

        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/api/extract-pdf", {
          method: "POST",
          body: formData,
        });
        const result = await response.json();
        if (!response.ok || !result.ok) {
          throw new Error(result.error || "PDF 整理失败");
        }
        return result;
      }

      async function searchKnowledgeBase(keyword) {
        const url = new URL("/api/knowledge-base", window.location.origin);
        if (keyword) url.searchParams.set("search", keyword);
        const response = await fetch(url);
        const result = await response.json();
        if (!response.ok || !result.ok) {
          throw new Error(result.error || "知识库查询失败");
        }
        return result.entries;
      }

      viewMode.addEventListener("change", renderResult);

      button.addEventListener("click", async () => {
        button.disabled = true;
        meta.textContent = "正在提取并整理...";
        output.value = "";

        try {
          const result = await extractPdfFromFile(input.files[0]);
          latestResult = result;
          renderResult();
          const ocrText = result.ocr.pages_used > 0 ? `；OCR页数：${result.ocr.pages_used}` : "";
          meta.textContent = `文件：${result.filename}；页数：${result.page_count}；段落：${result.organized.paragraphs.length}；知识库条目：${result.knowledge_base.entry_count}${ocrText}`;
        } catch (error) {
          meta.textContent = error.message;
        } finally {
          button.disabled = false;
        }
      });

      searchButton.addEventListener("click", async () => {
        searchButton.disabled = true;
        meta.textContent = "正在查询知识库出处...";
        try {
          const entries = await searchKnowledgeBase(searchInput.value.trim());
          viewMode.value = "knowledge";
          output.value = formatKnowledgeEntries(entries);
          meta.textContent = `查询到 ${entries.length} 条知识库出处`;
        } catch (error) {
          meta.textContent = error.message;
        } finally {
          searchButton.disabled = false;
        }
      });
    </script>
  </body>
</html>
"""


def normalize_pdf_text(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ocr_page(path: Path, page_index: int) -> tuple[str, str]:
    if fitz is None or pytesseract is None or Image is None:
        return "", "OCR dependencies are not installed"

    try:
        with fitz.open(str(path)) as document:
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
            text = pytesseract.image_to_string(image, lang=OCR_LANGUAGES)
            return normalize_pdf_text(text), ""
    except Exception as exc:
        return "", str(exc)


def extract_pdf(path: Path, filename: str) -> dict[str, Any]:
    reader = PdfReader(str(path))
    pages: list[dict[str, Any]] = []
    ocr_pages_used = 0
    ocr_errors: list[dict[str, Any]] = []

    for index, page in enumerate(reader.pages, start=1):
        text = normalize_pdf_text(page.extract_text() or "")
        extraction_method = "pdf_text"

        if len(text) < 20:
            ocr_text, ocr_error = ocr_page(path, index - 1)
            if ocr_text:
                text = ocr_text
                extraction_method = "ocr"
                ocr_pages_used += 1
            elif ocr_error:
                ocr_errors.append({"page": index, "error": ocr_error})

        pages.append(
            {
                "page": index,
                "text": text,
                "char_count": len(text),
                "extraction_method": extraction_method,
            }
        )

    full_text = "\n\n".join(page["text"] for page in pages if page["text"])
    organized = organize_text(full_text, pages)
    upload_id = uuid.uuid4().hex
    knowledge_entries = build_knowledge_entries(upload_id, filename, pages, organized)
    append_knowledge_entries(knowledge_entries)

    return {
        "upload_id": upload_id,
        "page_count": len(reader.pages),
        "char_count": len(full_text),
        "text": full_text,
        "pages": pages,
        "organized": organized,
        "ocr": {
            "enabled": fitz is not None and pytesseract is not None and Image is not None,
            "languages": OCR_LANGUAGES,
            "pages_used": ocr_pages_used,
            "errors": ocr_errors[:10],
        },
        "knowledge_base": {
            "entry_count": len(knowledge_entries),
            "entries": knowledge_entries,
        },
    }


def clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    return line


def looks_like_heading(line: str) -> bool:
    if not line or len(line) > 80:
        return False
    heading_patterns = [
        r"^\d+(\.\d+)*[.)、]?\s+.+",
        r"^(第[一二三四五六七八九十百千万0-9]+[章节部分篇]).+",
        r"^[A-Z][A-Z0-9\s:：,-]{4,}$",
        r"^(Abstract|Introduction|Conclusion|References|摘要|引言|结论|参考文献)\b",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in heading_patterns)


def split_paragraphs(text: str) -> list[str]:
    lines = [clean_line(line) for line in text.splitlines()]
    paragraphs: list[str] = []
    buffer: list[str] = []

    for line in lines:
        if not line:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue

        if looks_like_heading(line):
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            paragraphs.append(line)
            continue

        buffer.append(line)

    if buffer:
        paragraphs.append(" ".join(buffer).strip())

    return [paragraph for paragraph in paragraphs if paragraph]


def extract_key_items(text: str) -> dict[str, list[str]]:
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)))
    urls = sorted(set(re.findall(r"https?://[^\s)）]+", text)))
    phones = sorted(
        set(re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", text))
    )
    dates = sorted(
        set(
            re.findall(
                r"\b\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}日?\b|\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b",
                text,
            )
        )
    )
    return {
        "emails": emails,
        "urls": urls,
        "phones": phones[:20],
        "dates": dates[:30],
    }


def organize_text(full_text: str, pages: list[dict[str, Any]]) -> dict[str, Any]:
    paragraphs = split_paragraphs(full_text)
    headings = [paragraph for paragraph in paragraphs if looks_like_heading(paragraph)]
    key_items = extract_key_items(full_text)

    title = ""
    for paragraph in paragraphs[:8]:
        if 4 <= len(paragraph) <= 120:
            title = paragraph
            break

    page_summaries = []
    for page in pages:
        page_paragraphs = split_paragraphs(page["text"])
        page_summaries.append(
            {
                "page": page["page"],
                "paragraph_count": len(page_paragraphs),
                "preview": page_paragraphs[0][:220] if page_paragraphs else "",
            }
        )

    markdown_parts = [
        f"# {title or 'PDF 整理结果'}",
        "",
        "## 基本信息",
        f"- 页数：{len(pages)}",
        f"- 字符数：{len(full_text)}",
        f"- 段落数：{len(paragraphs)}",
    ]

    if headings:
        markdown_parts.extend(["", "## 识别到的章节/标题"])
        markdown_parts.extend(f"- {heading}" for heading in headings[:40])

    if any(key_items.values()):
        markdown_parts.extend(["", "## 识别到的关键信息"])
        for label, values in [
            ("邮箱", key_items["emails"]),
            ("网址", key_items["urls"]),
            ("电话", key_items["phones"]),
            ("日期", key_items["dates"]),
        ]:
            if values:
                markdown_parts.append(f"- {label}：{', '.join(values)}")

    markdown_parts.extend(["", "## 整理后的正文"])
    for paragraph in paragraphs:
        if looks_like_heading(paragraph):
            markdown_parts.extend(["", f"### {paragraph}", ""])
        else:
            markdown_parts.extend([paragraph, ""])

    return {
        "title": title,
        "headings": headings,
        "paragraphs": paragraphs,
        "key_items": key_items,
        "page_summaries": page_summaries,
        "markdown": "\n".join(markdown_parts).strip(),
    }


def entry_title(content: str, fallback: str) -> str:
    title = re.split(r"[。.!！?？\n]", content.strip())[0]
    title = title[:70].strip()
    return title or fallback


def build_knowledge_entries(
    upload_id: str,
    filename: str,
    pages: list[dict[str, Any]],
    organized: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for page in pages:
        page_number = page["page"]
        page_paragraphs = split_paragraphs(page["text"])

        for paragraph_index, paragraph in enumerate(page_paragraphs, start=1):
            if len(paragraph) < 8:
                continue

            kind = "heading" if looks_like_heading(paragraph) else "paragraph"
            entries.append(
                {
                    "id": f"{upload_id}-p{page_number}-{paragraph_index}",
                    "upload_id": upload_id,
                    "filename": filename,
                    "kind": kind,
                    "title": entry_title(paragraph, f"第 {page_number} 页第 {paragraph_index} 段"),
                    "content": paragraph,
                    "source": {
                        "file": filename,
                        "page": page_number,
                        "paragraph": paragraph_index,
                        "label": f"{filename} / 第 {page_number} 页 / 第 {paragraph_index} 段",
                    },
                }
            )

    if organized["key_items"]:
        for item_type, values in organized["key_items"].items():
            for value in values:
                entries.append(
                    {
                        "id": f"{upload_id}-{item_type}-{uuid.uuid4().hex[:8]}",
                        "upload_id": upload_id,
                        "filename": filename,
                        "kind": "key_item",
                        "title": value,
                        "content": value,
                        "source": {
                            "file": filename,
                            "page": None,
                            "paragraph": None,
                            "label": f"{filename} / 关键信息 / {item_type}",
                        },
                    }
                )

    return entries


def append_knowledge_entries(entries: list[dict[str, Any]]) -> None:
    if not entries:
        return

    with KNOWLEDGE_BASE_PATH.open("a", encoding="utf-8") as file:
        for entry in entries:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_knowledge_entries(search: str = "", limit: int = 200) -> list[dict[str, Any]]:
    if not KNOWLEDGE_BASE_PATH.exists():
        return []

    search_lower = search.lower().strip()
    entries: list[dict[str, Any]] = []

    with KNOWLEDGE_BASE_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            entry = json.loads(line)
            searchable = f"{entry.get('title', '')} {entry.get('content', '')} {entry.get('filename', '')}".lower()
            if search_lower and search_lower not in searchable:
                continue
            entries.append(entry)

    return entries[-limit:]


def parse_multipart_file(body: bytes, content_type: str) -> tuple[str, bytes]:
    match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
    if not match:
        raise ValueError("Missing multipart boundary")

    boundary = match.group("boundary").strip('"')
    delimiter = ("--" + boundary).encode()

    for part in body.split(delimiter):
        if b"Content-Disposition:" not in part:
            continue

        header_blob, _, file_bytes = part.partition(b"\r\n\r\n")
        headers = header_blob.decode("utf-8", errors="replace")
        if 'name="file"' not in headers:
            continue

        filename_match = re.search(r'filename="([^"]*)"', headers)
        filename = filename_match.group(1) if filename_match else "upload.pdf"
        return filename, file_bytes.rstrip(b"\r\n-")

    raise ValueError('Missing file field. Use form field name "file".')


class PDFExtractHandler(BaseHTTPRequestHandler):
    server_version = "PDFExtractAPI/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path in ("/", "/index.html", "/pdf-demo.html"):
            self.send_html(APP_HTML)
            return

        if parsed_url.path == "/health":
            self.send_json({"ok": True, "service": "pdf-extract-api"})
            return

        if parsed_url.path == "/api/knowledge-base":
            query = parse_qs(parsed_url.query)
            search = query.get("search", [""])[0]
            limit = int(query.get("limit", ["200"])[0])
            entries = read_knowledge_entries(search=search, limit=limit)
            self.send_json({"ok": True, "entry_count": len(entries), "entries": entries})
            return

        self.send_json(
            {
                "ok": True,
                "message": "POST a PDF to /api/extract-pdf, or GET /api/knowledge-base.",
            }
        )

    def do_POST(self) -> None:
        if self.path != "/api/extract-pdf":
            self.send_error_json(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("Empty request body")
            if length > MAX_UPLOAD_BYTES:
                raise ValueError("PDF is too large. Max size is 50MB.")

            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                raise ValueError("Content-Type must be multipart/form-data")

            body = self.rfile.read(length)
            filename, file_bytes = parse_multipart_file(body, content_type)
            if not filename.lower().endswith(".pdf"):
                raise ValueError("Only .pdf files are supported")
            if not file_bytes.startswith(b"%PDF"):
                raise ValueError("Uploaded file does not look like a PDF")

            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).name)
            upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
            upload_path.write_bytes(file_bytes)

            result = extract_pdf(upload_path, filename)
            self.send_json({"ok": True, "filename": filename, **result})
        except Exception as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status)

    def send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PDFExtractHandler)
    print(f"PDF extraction app running at http://127.0.0.1:{PORT}")
    print(f"LAN sharing address uses this computer's IP, for example http://YOUR-IP:{PORT}")
    print("POST /api/extract-pdf with multipart field name 'file'")
    server.serve_forever()


if __name__ == "__main__":
    main()
