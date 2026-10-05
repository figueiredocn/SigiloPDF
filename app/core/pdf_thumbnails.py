"""Miniaturas locais em memória; nenhuma página de saída usa estas imagens."""

from collections.abc import Callable
from pathlib import Path

import pymupdf

from app.core.pdf_info import resolve_local_path
from app.core.reorder_pdf import ReorderPdfError

MAX_PREVIEW_PIXELS = 4_000_000


def _render(page: pymupdf.Page, scale: float) -> bytes:
    pixels = max(1, page.rect.width * page.rect.height * scale ** 2)
    scale *= min(1.0, (MAX_PREVIEW_PIXELS / pixels) ** 0.5)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
    return pixmap.tobytes("png")


def render_page_preview(source: str | Path, index: int, zoom: float = 1.0,
                        max_size: int | None = None) -> bytes:
    try:
        path = resolve_local_path(source)
        with pymupdf.open(path) as document:
            if document.is_encrypted or not document.is_pdf:
                raise ReorderPdfError("Não foi possível abrir a pré-visualização deste PDF.")
            if not 0 <= index < len(document):
                raise ReorderPdfError("Esta página não existe no PDF.")
            if not 0.25 <= zoom <= 2.0:
                raise ReorderPdfError("Escolha um zoom entre 25% e 200%.")
            page = document[index]
            scale = max_size / max(page.rect.width, page.rect.height) if max_size else zoom
            return _render(page, scale)
    except ReorderPdfError:
        raise
    except Exception as error:
        raise ReorderPdfError(f"Não foi possível gerar a pré-visualização da página {index + 1}.") from error


def render_thumbnails(source: str | Path, receive: Callable[[int, bytes], None],
                      cancelled: Callable[[], bool], max_size: int = 180,
                      failed: Callable[[int, str], None] | None = None) -> None:
    path = resolve_local_path(source)
    try:
        with pymupdf.open(path) as document:
            if document.is_encrypted:
                raise ReorderPdfError("Este PDF está protegido por senha.")
            for index in range(len(document)):
                if cancelled():
                    return
                try:
                    page = document[index]
                    receive(index, _render(page, max_size / max(page.rect.width, page.rect.height)))
                except Exception:
                    message = f"Não foi possível gerar a pré-visualização da página {index + 1}."
                    if failed:
                        failed(index, message)
                    else:
                        receive(index, b"")
    except ReorderPdfError:
        raise
    except Exception as error:
        raise ReorderPdfError("Não foi possível carregar as miniaturas deste PDF.") from error
