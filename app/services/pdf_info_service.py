"""Ponto de entrada da ferramenta de informações para a interface."""

from pathlib import Path

from app.core.pdf_info import PdfInfo, PdfInfoError, read_pdf_info

__all__ = ["PdfInfo", "PdfInfoError", "PdfInfoService"]


class PdfInfoService:
    def inspect(self, path: str | Path) -> PdfInfo:
        return read_pdf_info(path)
