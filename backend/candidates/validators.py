"""Upload validation for PDF and DOCX resumes."""

import hashlib
import zipfile
from pathlib import PurePath

from django.conf import settings
from rest_framework import serializers

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def safe_filename(uploaded_file):
    return (uploaded_file.name or "resume").replace("\\", "/").split("/")[-1][:255]


def validate_resume_upload(uploaded_file):
    filename = safe_filename(uploaded_file)
    suffix = PurePath(filename).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise serializers.ValidationError("Only PDF and DOCX resumes are supported.")
    max_bytes = settings.RESUME_MAX_FILE_SIZE_BYTES
    if uploaded_file.size <= 0:
        raise serializers.ValidationError("The uploaded file is empty.")
    if uploaded_file.size > max_bytes:
        raise serializers.ValidationError(f"Resume exceeds the {settings.RESUME_MAX_FILE_SIZE_MB} MB file-size limit.")

    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(1024)
        uploaded_file.seek(0)
        if suffix == ".pdf":
            if b"%PDF-" not in header:
                raise serializers.ValidationError("The file extension does not match a valid PDF file.")
            return PDF_MIME
        if not header.startswith(b"PK"):
            raise serializers.ValidationError("The file extension does not match a valid DOCX file.")
        with zipfile.ZipFile(uploaded_file) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise serializers.ValidationError("The uploaded ZIP file is not a valid DOCX document.")
            members = archive.infolist()
            if any(member.flag_bits & 0x1 for member in members):
                raise serializers.ValidationError("Encrypted DOCX files are not supported.")
            if sum(item.file_size for item in members) > 50 * 1024 * 1024:
                raise serializers.ValidationError("The uncompressed DOCX content exceeds the safety limit.")
            if any(item.compress_size > 0 and item.file_size / item.compress_size > 200 for item in members):
                raise serializers.ValidationError("The DOCX archive has an unsafe compression ratio.")
            if archive.testzip() is not None:
                raise serializers.ValidationError("The DOCX archive is corrupted.")
        return DOCX_MIME
    except serializers.ValidationError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        raise serializers.ValidationError("The uploaded document is invalid or corrupted.") from exc
    finally:
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass


def calculate_sha256(uploaded_file):
    digest = hashlib.sha256()
    uploaded_file.seek(0)
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()
