from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.preview_service import PreviewService, ReorderPdfError


class PreviewSignals(QObject):
    image = Signal(int, int, bytes)
    failed = Signal(int, int, str)
    finished = Signal(object)


class PreviewWorker(QRunnable):
    def __init__(self, source: str, generation: int, index: int | None = None,
                 zoom: float = 1.0, max_size: int | None = None) -> None:
        super().__init__()
        self.source, self.generation, self.index = source, generation, index
        self.zoom, self.max_size = zoom, max_size
        self.cancelled = Event()
        self.signals = PreviewSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.cancelled.is_set():
                return
            service = PreviewService()
            def receive(index: int, data: bytes) -> None:
                if not self.cancelled.is_set():
                    self.signals.image.emit(self.generation, index, data)
            def fail(index: int, message: str) -> None:
                if not self.cancelled.is_set():
                    self.signals.failed.emit(self.generation, index, message)
            if self.index is None:
                service.thumbnails(self.source, receive, fail, self.cancelled.is_set)
            else:
                receive(self.index, service.page(self.source, self.index, self.zoom, self.max_size))
        except Exception as error:
            message = str(error) if isinstance(error, ReorderPdfError) else "Não foi possível carregar a pré-visualização."
            self.signals.failed.emit(self.generation, self.index if self.index is not None else -1, message)
        finally:
            self.signals.finished.emit(self)
