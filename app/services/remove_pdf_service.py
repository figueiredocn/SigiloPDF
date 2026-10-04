from collections.abc import Callable
from pathlib import Path

from app.core.page_selection import PageSelectionError
from app.core.pdf_info import PdfInfo, PdfInfoError, read_pdf_info
from app.core.remove_pdf import RemovalSummary, RemovePdfError, remove_pages, summarize_removal
from app.services.extract_pdf_service import ExtractPdfService

__all__ = ["RemovePdfError", "RemovePdfService", "RemovalSummary"]


class RemovePdfService(ExtractPdfService):
    """Usa o contrato dos workers de páginas para produzir uma nova versão."""

    def inspect(self, path: str) -> PdfInfo:
        try:
            info = read_pdf_info(path)
        except PdfInfoError as error:
            raise RemovePdfError(str(error)) from error
        if info.encrypted:
            raise RemovePdfError("PDFs criptografados não podem ter páginas removidas nesta versão.")
        if not info.page_count:
            raise RemovePdfError("O PDF não possui páginas.")
        return info

    def removal_summary(self, expression: str, total_pages: int) -> RemovalSummary:
        try:
            return summarize_removal(expression, total_pages)
        except PageSelectionError as error:
            raise RemovePdfError(str(error)) from error

    def extract(self, source: str, output: str, expression: str, progress: Callable[[int, str], None]) -> Path:
        return remove_pages(source, output, expression, progress)
