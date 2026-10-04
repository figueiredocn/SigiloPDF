from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

from app.core.merge_pdf import MergePdfError, Progress, merge_pdfs
from app.core.pdf_info import PdfInfoError, read_pdf_info

__all__ = ["MergePdfError", "MergePdfService", "MergeInput"]


@dataclass(frozen=True)
class MergeInput:
    path: str
    name: str
    page_count: int


class MergePdfService:
    def inspect(self, path: str) -> MergeInput:
        try:
            info = read_pdf_info(path)
        except PdfInfoError as error:
            raise MergePdfError(str(error)) from error
        if info.encrypted:
            raise MergePdfError("PDFs criptografados não podem ser juntados nesta versão.")
        if not info.page_count:
            raise MergePdfError("O PDF não possui páginas. Selecione outro arquivo.")
        return MergeInput(info.path, info.name, info.page_count)

    def merge(self, inputs: Sequence[str], output: str, progress: Progress) -> Path:
        return merge_pdfs(inputs, output, progress)
