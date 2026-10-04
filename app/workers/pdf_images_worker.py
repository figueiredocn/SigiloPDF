from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.pdf_images_service import ExportCancelled, PdfImagesError, PdfImagesService
from app.services.reorder_pdf_service import ReorderPdfError


class PdfImagesSignals(QObject):
    inspected = Signal(object)
    thumbnail = Signal(int, bytes)
    progress = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class PdfImagesWorker(QRunnable):
    def __init__(self, service: PdfImagesService, source: str, folder: str | None = None,
                 pages: str | None = None, image_format: str = "PNG", dpi: int = 150, quality: int = 90) -> None:
        super().__init__()
        self.service, self.source, self.folder, self.pages = service, source, folder, pages
        self.image_format, self.dpi, self.quality = image_format, dpi, quality
        self.cancelled = Event()
        self.signals = PdfImagesSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.folder is None:
                self.signals.inspected.emit(self.service.inspect(self.source))
                self.service.thumbnails(self.source, self.signals.thumbnail.emit, self.cancelled.is_set)
            else:
                result = self.service.export(self.source, self.folder, self.pages, self.image_format, self.dpi,
                                             self.quality, self.signals.progress.emit, self.cancelled.is_set)
                self.signals.succeeded.emit(result)
        except ExportCancelled as error:
            self.signals.failed.emit(str(error))
        except Exception as error:
            message = str(error) if isinstance(error, (PdfImagesError, ReorderPdfError)) else "Não foi possível concluir a operação. Tente novamente."
            self.signals.failed.emit(message)
        finally:
            self.signals.finished.emit()
