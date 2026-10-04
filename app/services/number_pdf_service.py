from collections.abc import Callable
from pathlib import Path

from app.core.number_pdf import FONT_SIZES, FORMATS, POSITIONS, NumberSettings, number_label, number_pdf, selected_number_pages
from app.core.pdf_edit import PdfEditError
from app.core.pdf_info import PdfInfoError, read_pdf_info
from app.services.extract_pdf_service import ExtractPdfService, PdfInfo

__all__ = ["NumberPdfService", "NumberSettings", "PdfEditError", "POSITIONS", "FORMATS", "FONT_SIZES", "number_label"]


class NumberPdfService(ExtractPdfService):
    def __init__(self, settings: NumberSettings = NumberSettings()) -> None:
        self.settings = settings

    def inspect(self, path: str) -> PdfInfo:
        try:
            info = read_pdf_info(path)
        except PdfInfoError as error:
            raise PdfEditError(str(error)) from error
        if info.encrypted:
            raise PdfEditError("Este PDF está protegido por senha.")
        if not info.page_count:
            raise PdfEditError("O PDF precisa conter pelo menos uma página.")
        return info

    def summarize_numbering(self, settings: NumberSettings, total: int) -> list[int]:
        return selected_number_pages(settings, total)

    def extract(self, source: str, output: str, expression: str, progress: Callable[[int, str], None]) -> Path:
        return number_pdf(source, output, self.settings, progress)
