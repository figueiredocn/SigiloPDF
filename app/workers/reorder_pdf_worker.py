from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.reorder_pdf_service import ReorderPdfError, ReorderPdfService


class ReorderSignals(QObject):
    inspected = Signal(object)
    thumbnail = Signal(int, bytes)
    progress = Signal(int, str)
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class ReorderWorker(QRunnable):
    def __init__(self, service: ReorderPdfService, source: str,
                 order: tuple[int, ...] | None = None, output: str = "") -> None:
        super().__init__()
        self.service, self.source, self.order, self.output = service, source, order, output
        self.signals = ReorderSignals()
        self.cancelled = Event()

    @Slot()
    def run(self) -> None:
        try:
            if self.order is None:
                self.signals.inspected.emit(self.service.inspect(self.source))
                self.service.thumbnails(self.source, self.signals.thumbnail.emit, self.cancelled.is_set)
            else:
                result = self.service.save(self.source, self.order, self.output, self.signals.progress.emit)
                self.signals.succeeded.emit(str(result))
        except ReorderPdfError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            self.signals.failed.emit("Não foi possível concluir a operação. Tente novamente.")
        finally:
            self.signals.finished.emit()
