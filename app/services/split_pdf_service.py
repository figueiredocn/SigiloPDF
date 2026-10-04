from pathlib import Path

from app.core.pdf_info import PdfInfo, PdfInfoError, read_pdf_info
from app.core.split_pdf import Progress, SplitMode, SplitPdfError, split_pdf

__all__ = ["PdfInfo", "SplitMode", "SplitPdfError", "SplitPdfService"]


class SplitPdfService:
    def inspect(self, path: str) -> PdfInfo:
        try:
            info = read_pdf_info(path)
        except PdfInfoError as error:
            raise SplitPdfError(str(error)) from error
        if info.encrypted:
            raise SplitPdfError("PDFs criptografados não podem ser divididos nesta versão.")
        if not info.page_count:
            raise SplitPdfError("O PDF não possui páginas para dividir.")
        return info

    def split(self, path: str, folder: str, mode: SplitMode, expression: str, progress: Progress) -> list[Path]:
        return split_pdf(path, folder, mode, expression, progress)
