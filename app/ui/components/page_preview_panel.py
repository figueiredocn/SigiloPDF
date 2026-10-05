from collections.abc import Callable

from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import QAbstractItemView, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.services.preview_service import PageSelectionError, PreviewService, ReorderPdfError
from app.ui.components.page_thumbnail_list import PageThumbnailList, ROTATION_ROLE
from app.ui.components.pdf_preview_dialog import PdfPreviewDialog
from app.workers.preview_worker import PreviewWorker


class PagePreviewPanel(QWidget):
    def __init__(self, parent: QWidget | None = None, reorder: bool = False) -> None:
        super().__init__(parent)
        self.source, self.generation, self.loaded = "", 0, set()
        self.fingerprint: tuple[int, int] | None = None
        self.rendering = False
        self.closing = False
        self.workers: set[PreviewWorker] = set()
        self.pending: set[int] = set()
        self.dialog: PdfPreviewDialog | None = None
        self.expression: QLineEdit | None = None
        self.choose_mode: Callable[[], None] = lambda: None
        self.service = PreviewService()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.pages = PageThumbnailList()
        if not reorder:
            self.pages.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        layout.addWidget(self.pages)
        self.status = QLabel("Duplo clique para ampliar. Ctrl/Shift para selecionar páginas.")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.pages.page_activated.connect(self.open_page)
        self.pages.thumbnail_requested.connect(self.request_thumbnail)
        self.pages.itemSelectionChanged.connect(self.visual_selection)

    def reset(self) -> None:
        self.generation += 1
        for worker in self.workers:
            worker.cancelled.set()
        if self.dialog is not None:
            self.dialog.close()
        self.pages.clear()
        self.pending.clear()
        self.loaded.clear()
        self.source = ""
        self.fingerprint = None
        self.rendering = False

    def load(self, source: str, total: int, external: bool = False) -> None:
        if self.closing:
            return
        self.reset()
        self.source = source
        try:
            self.fingerprint = self.service.fingerprint(source)
        except ReorderPdfError as error:
            self.status.setText(str(error))
            return
        self.rendering = True
        self.pages.populate(total)
        self.sync_text()
        self.status.setText(f"Carregando páginas 0 de {total}…")
        if not external:
            self._launch(PreviewWorker(source, self.generation))

    def bind(self, expression: QLineEdit, choose_mode: Callable[[], None] = lambda: None) -> None:
        self.expression, self.choose_mode = expression, choose_mode
        expression.textChanged.connect(self.sync_text)

    def sync_text(self, *_args: object) -> None:
        if self.expression is None or not self.pages.count():
            return
        try:
            indices = self.service.selection(self.expression.text(), self.pages.count()) if self.expression.text().strip() else ()
            self.pages.select_pages(indices)
        except PageSelectionError:
            self.pages.select_pages(())

    def visual_selection(self) -> None:
        if self.expression is not None:
            indices = self.pages.selected_pages()
            self.choose_mode()
            self.expression.setText(self.service.expression(indices))

    def _launch(self, worker: PreviewWorker) -> None:
        self.workers.add(worker)
        worker.signals.image.connect(self.thumbnail)
        worker.signals.failed.connect(self.failed)
        worker.signals.finished.connect(self.finished)
        QThreadPool.globalInstance().start(worker)

    @Slot(int, int, bytes)
    def thumbnail(self, generation: int, index: int, data: bytes) -> None:
        if generation == self.generation:
            self.pages.thumbnail(index, data)
            self.loaded.add(index)
            self.pending.discard(index)
            self.status.setText(f"Carregando páginas {len(self.loaded)} de {self.pages.count()}…")

    @Slot(int, int, str)
    def failed(self, generation: int, index: int, message: str) -> None:
        if generation == self.generation:
            if index >= 0:
                self.pages.mark_error(index, message)
                self.loaded.add(index)
                self.pending.discard(index)
            self.status.setText(message)

    @Slot(object)
    def finished(self, worker: PreviewWorker) -> None:
        self.workers.discard(worker)
        if worker.generation == self.generation:
            if worker.index is None:
                self.rendering = False
                self.status.setText(f"{len(self.loaded)} de {self.pages.count()} prévias concluídas. Duplo clique para ampliar; Ctrl/Shift para selecionar.")
            self.pages.request_visible()

    def complete(self) -> None:
        self.rendering = False
        if not self.closing:
            self.pages.request_visible()

    def unchanged(self) -> bool:
        try:
            if self.fingerprint == self.service.fingerprint(self.source):
                return True
        except ReorderPdfError:
            pass
        self.reset()
        self.status.setText("O PDF foi alterado ou não está disponível. Selecione-o novamente para atualizar as prévias.")
        return False

    @Slot(int)
    def request_thumbnail(self, index: int) -> None:
        if not self.closing and self.source and not self.rendering and index not in self.pending and self.unchanged():
            self.pending.add(index)
            self._launch(PreviewWorker(self.source, self.generation, index, max_size=180))

    @Slot(int)
    def open_page(self, index: int) -> None:
        if not self.source or index not in self.pages.order() or not self.unchanged():
            return
        if self.dialog is not None:
            self.dialog.close()
        rotations = {original: self.pages._items[original].data(ROTATION_ROLE) or 0 for original in self.pages.order()}
        self.dialog = PdfPreviewDialog(self.source, self.pages.order(), index, rotations, self)
        dialog = self.dialog
        dialog.destroyed.connect(lambda _object=None: self.dialog_destroyed(dialog))
        self.dialog.show()

    @Slot(object)
    def dialog_destroyed(self, dialog: object) -> None:
        if self.dialog is dialog:
            self.dialog = None

    def prepare_close(self) -> None:
        self.closing = True
        self.generation += 1
        for worker in self.workers:
            worker.cancelled.set()
        if self.dialog is not None:
            self.dialog.close()

    def has_pending_work(self) -> bool:
        return bool(self.workers) or any(dialog.workers for dialog in self.findChildren(PdfPreviewDialog))
