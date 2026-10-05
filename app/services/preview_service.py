from collections.abc import Callable

from app.core.page_selection import PageSelectionError, parse_page_selection, selection_label
from app.core.pdf_thumbnails import render_page_preview, render_thumbnails
from app.core.reorder_pdf import ReorderPdfError
from app.core.pdf_info import resolve_local_path

__all__ = ["PreviewService", "ReorderPdfError", "PageSelectionError"]


class PreviewService:
    def fingerprint(self, source: str) -> tuple[int, int]:
        try:
            stat = resolve_local_path(source).stat()
            return stat.st_mtime_ns, stat.st_size
        except Exception as error:
            raise ReorderPdfError("O PDF não está mais disponível. Selecione-o novamente.") from error

    def thumbnails(self, source: str, receive: Callable[[int, bytes], None],
                   failed: Callable[[int, str], None], cancelled: Callable[[], bool]) -> None:
        render_thumbnails(source, receive, cancelled, failed=failed)

    def page(self, source: str, index: int, zoom: float = 1.0, max_size: int | None = None) -> bytes:
        return render_page_preview(source, index, zoom, max_size)

    def selection(self, expression: str, total: int) -> tuple[int, ...]:
        return tuple(page - 1 for page in parse_page_selection(expression, total, preserve_order=True))

    def expression(self, indices: tuple[int, ...]) -> str:
        return selection_label([index + 1 for index in indices], max_length=None)
