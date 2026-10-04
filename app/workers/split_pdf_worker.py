from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.split_pdf_service import SplitMode, SplitPdfError, SplitPdfService


class SplitSignals(QObject):
    inspected = Signal(object)
    progress = Signal(int, str)
    succeeded = Signal(list)
    failed = Signal(str)
    finished = Signal()


class InspectSplitWorker(QRunnable):
    def __init__(self, service: SplitPdfService, path: str) -> None:
        super().__init__()
        self.service, self.path = service, path
        self.signals = SplitSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.inspected.emit(self.service.inspect(self.path))
        except SplitPdfError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            self.signals.failed.emit("Não foi possível verificar o PDF. Tente novamente.")
        finally:
            self.signals.finished.emit()


class SplitPdfWorker(QRunnable):
    def __init__(self, service: SplitPdfService, path: str, folder: str, mode: SplitMode, expression: str) -> None:
        super().__init__()
        self.service, self.path, self.folder = service, path, folder
        self.mode, self.expression = mode, expression
        self.signals = SplitSignals()

    @Slot()
    def run(self) -> None:
        try:
            results = self.service.split(self.path, self.folder, self.mode, self.expression, self.signals.progress.emit)
            self.signals.succeeded.emit([str(path) for path in results])
        except SplitPdfError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            self.signals.failed.emit("Não foi possível concluir a divisão. Tente novamente.")
        finally:
            self.signals.finished.emit()
