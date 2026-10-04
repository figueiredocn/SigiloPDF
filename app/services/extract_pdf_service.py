from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path

from app.core.extract_pdf import ExtractPdfError, extract_pages
from app.core.page_selection import PageSelectionError, parse_page_selection
from app.core.pdf_info import PdfInfo, PdfInfoError, read_pdf_info

__all__ = ["PdfInfo", "ExtractionSummary", "ExtractPdfError", "ExtractPdfService"]


@dataclass(frozen=True)
class ExtractionSummary:
    pages: tuple[int, ...]


class ExtractPdfService:
    def inspect(self, path: str) -> PdfInfo:
        try:
            info = read_pdf_info(path)
        except PdfInfoError as error:
            raise ExtractPdfError(str(error)) from error
        if info.encrypted:
            raise ExtractPdfError("PDFs criptografados não podem ser extraídos nesta versão.")
        if not info.page_count:
            raise ExtractPdfError("O PDF não possui páginas para extrair.")
        return info

    def summarize(self, expression: str, total_pages: int) -> ExtractionSummary:
        try:
            return ExtractionSummary(tuple(parse_page_selection(expression, total_pages, preserve_order=True)))
        except PageSelectionError as error:
            raise ExtractPdfError(str(error)) from error

    def extract(self, source: str, output: str, expression: str, progress: Callable[[int, str], None]) -> Path:
        return extract_pages(source, output, expression, progress)
