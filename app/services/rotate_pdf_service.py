from collections.abc import Callable
from pathlib import Path

from app.core.page_selection import PageSelectionError
from app.core.pdf_info import PdfInfo, PdfInfoError, read_pdf_info
from app.core.rotate_pdf import RotationSummary, RotatePdfError, rotate_pages, summarize_rotation
from app.services.extract_pdf_service import ExtractPdfService

__all__ = ["RotatePdfService", "RotatePdfError", "RotationSummary"]


class RotatePdfService(ExtractPdfService):
    def __init__(self, angle: int = 90, all_pages: bool = True) -> None:
        self.angle, self.all_pages = angle, all_pages

    def inspect(self, path: str) -> PdfInfo:
        try:
            info = read_pdf_info(path)
        except PdfInfoError as error:
            raise RotatePdfError(str(error)) from error
        if info.encrypted:
            raise RotatePdfError("PDFs criptografados não podem ser girados nesta versão.")
        if not info.page_count:
            raise RotatePdfError("O PDF não possui páginas para girar.")
        return info

    def rotation_summary(self, expression: str, total_pages: int, angle: int, all_pages: bool) -> RotationSummary:
        try:
            return summarize_rotation(expression, total_pages, angle, all_pages)
        except PageSelectionError as error:
            raise RotatePdfError(str(error)) from error

    def extract(self, source: str, output: str, expression: str, progress: Callable[[int, str], None]) -> Path:
        return rotate_pages(source, output, self.angle, expression, all_pages=self.all_pages, progress=progress)
