from collections.abc import Callable
from pathlib import Path

from app.core.pdf_metadata import ANONYMITY_WARNING, EDITABLE_FIELDS, MetadataSnapshot, edit_metadata, read_metadata
from app.core.pdf_edit import PdfEditError
from app.services.extract_pdf_service import ExtractPdfService

__all__ = ["MetadataService", "MetadataSnapshot", "EDITABLE_FIELDS", "ANONYMITY_WARNING", "PdfEditError"]


class MetadataService(ExtractPdfService):
    def __init__(self, fields: dict[str, str] | None = None, clear: bool = False) -> None:
        self.fields, self.clear = dict(fields or {}), clear

    def inspect(self, path: str) -> MetadataSnapshot:
        return read_metadata(path)

    def extract(self, source: str, output: str, expression: str, progress: Callable[[int, str], None]) -> Path:
        progress(10, "Removendo metadados pessoais…" if self.clear else "Atualizando os metadados…")
        result = edit_metadata(source, output, self.fields, clear=self.clear)
        progress(100, "Metadados processados.")
        return result
