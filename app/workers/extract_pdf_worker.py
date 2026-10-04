from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.extract_pdf_service import ExtractPdfError, ExtractPdfService


class ExtractSignals(QObject):
    inspected = Signal(object)
    progress = Signal(int, str)
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class InspectExtractWorker(QRunnable):
    def __init__(self, service: ExtractPdfService, path: str) -> None:
        super().__init__()
        self.service, self.path = service, path
        self.signals = ExtractSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.inspected.emit(self.service.inspect(self.path))
        except ExtractPdfError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            self.signals.failed.emit("Não foi possível verificar o PDF. Tente novamente.")
        finally:
            self.signals.finished.emit()


class ExtractPdfWorker(QRunnable):
    def __init__(self, service: ExtractPdfService, source: str, output: str, expression: str) -> None:
        super().__init__()
        self.service, self.source, self.output = service, source, output
        self.expression = expression
        self.signals = ExtractSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.service.extract(self.source, self.output, self.expression, self.signals.progress.emit)
            self.signals.succeeded.emit(str(result))
        except ExtractPdfError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            self.signals.failed.emit("Não foi possível concluir a operação. Tente novamente.")
        finally:
            self.signals.finished.emit()
