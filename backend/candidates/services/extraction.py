"""Local PDF/DOCX text extraction. OCR is intentionally not performed here."""

from dataclasses import dataclass
from pathlib import PurePath

from docx import Document
from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    metadata: dict
    warnings: list[str]


class ResumeExtractionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _clean_text(value):
    lines = [line.strip() for line in value.replace("\x00", " ").splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_pdf(file_obj):
    try:
        reader = PdfReader(file_obj, strict=False)
        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
            except Exception:
                decrypted = 0
            if not decrypted:
                raise ResumeExtractionError("PASSWORD_PROTECTED", "This PDF is password-protected. Provide an unlocked file or review it manually.")
        page_text = [(page.extract_text() or "") for page in reader.pages]
    except ResumeExtractionError:
        raise
    except Exception as exc:
        raise ResumeExtractionError("PDF_READ_ERROR", "The PDF could not be read. Upload another copy or review it manually.") from exc
    text = _clean_text("\n".join(page_text))
    if not text:
        raise ResumeExtractionError("NO_SELECTABLE_TEXT", "No selectable text was found. Scanned PDFs require OCR or manual review.")
    warnings = ["Very little text was extracted; verify the resume manually."] if len(text) < 100 else []
    return ExtractionResult(text, {"format":"pdf","page_count":len(page_text),"text_characters":len(text),"extractor":"pypdf"}, warnings)


def _extract_docx(file_obj):
    try:
        document = Document(file_obj)
        parts = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        text = _clean_text("\n".join(parts))
    except Exception as exc:
        raise ResumeExtractionError("DOCX_READ_ERROR", "The DOCX document could not be read. Upload another copy or review it manually.") from exc
    if not text:
        raise ResumeExtractionError("NO_SELECTABLE_TEXT", "No text was found in the DOCX document. Review it manually.")
    warnings = ["Very little text was extracted; verify the resume manually."] if len(text) < 100 else []
    return ExtractionResult(text, {"format":"docx","paragraph_count":len(document.paragraphs),"table_count":len(document.tables),"text_characters":len(text),"extractor":"python-docx"}, warnings)


def extract_resume_text(file_obj, filename):
    suffix = PurePath(filename.replace("\\", "/")).suffix.lower()
    file_obj.seek(0)
    if suffix == ".pdf":
        result = _extract_pdf(file_obj)
    elif suffix == ".docx":
        result = _extract_docx(file_obj)
    else:
        raise ResumeExtractionError("UNSUPPORTED_FILE_TYPE", "Only PDF and DOCX files are supported.")
    file_obj.seek(0)
    return result
