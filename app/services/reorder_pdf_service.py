from collections.abc import Callable, Sequence
from pathlib import Path

from app.core.pdf_info import PdfInfo, PdfInfoError, read_pdf_info
from app.core.pdf_thumbnails import render_thumbnails
from app.core.reorder_pdf import ReorderPdfError, reorder_pdf

__all__ = ["ReorderPdfService", "ReorderPdfError", "PdfInfo"]


class ReorderPdfService:
    def inspect(self, path: str) -> PdfInfo:
        try:
            info = read_pdf_info(path)
        except PdfInfoError as error:
            raise ReorderPdfError(str(error)) from error
        if info.encrypted:
            raise ReorderPdfError("Este PDF está protegido por senha.")
        if not info.page_count:
            raise ReorderPdfError("O PDF não possui páginas para organizar.")
        return info

    def thumbnails(self, path: str, receive: Callable[[int, bytes], None], cancelled: Callable[[], bool]) -> None:
        render_thumbnails(path, receive, cancelled)

    def save(self, source: str, order: Sequence[int], output: str, progress: Callable[[int, str], None]) -> Path:
        return reorder_pdf(source, order, output, progress)
