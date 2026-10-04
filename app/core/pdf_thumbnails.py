"""Miniaturas locais em memória; nenhuma página de saída usa estas imagens."""

from collections.abc import Callable
from pathlib import Path

import pymupdf

from app.core.pdf_info import resolve_local_path
from app.core.reorder_pdf import ReorderPdfError


def render_thumbnails(source: str | Path, receive: Callable[[int, bytes], None],
                      cancelled: Callable[[], bool], max_size: int = 180) -> None:
    path = resolve_local_path(source)
    try:
        with pymupdf.open(path) as document:
            if document.is_encrypted:
                raise ReorderPdfError("Este PDF está protegido por senha.")
            for index in range(len(document)):
                if cancelled():
                    return
                page = document[index]
                scale = max_size / max(page.rect.width, page.rect.height)
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
                receive(index, pixmap.tobytes("png"))
    except ReorderPdfError:
        raise
    except Exception as error:
        raise ReorderPdfError("Não foi possível carregar as miniaturas deste PDF.") from error
