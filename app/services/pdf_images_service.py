from collections.abc import Callable
from pathlib import Path

from app.core.pdf_to_images import ExportCancelled, JPEG_QUALITIES, RESOLUTIONS, PdfImagesError, pdf_to_images
from app.core.reorder_pdf import ReorderPdfError
from app.services.reorder_pdf_service import PdfInfo, ReorderPdfService

__all__ = ["PdfImagesService", "PdfImagesError", "ExportCancelled", "PdfInfo", "JPEG_QUALITIES", "RESOLUTIONS"]


class PdfImagesService(ReorderPdfService):
    def inspect(self, path: str) -> PdfInfo:
        try:
            return super().inspect(path)
        except ReorderPdfError as error:
            raise PdfImagesError(str(error)) from error

    def export(self, source: str, folder: str, pages: str | None, image_format: str, dpi: int, quality: int,
               progress: Callable[[int, str], None], cancelled: Callable[[], bool]) -> list[Path]:
        return pdf_to_images(source, folder, pages, image_format, dpi, quality, progress, cancelled)
