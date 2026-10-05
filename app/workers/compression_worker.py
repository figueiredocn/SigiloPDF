from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.compression_service import (CompressionError, CompressionOptions,
                                              CompressionService, PasswordRequired)


class CompressionSignals(QObject):
    succeeded = Signal(str, object)
    failed = Signal(str)
    password_required = Signal()
    progress = Signal(int, str)
    finished = Signal()


class CompressionWorker(QRunnable):
    def __init__(self, service: CompressionService, action: str, source: str = "",
                 options: CompressionOptions = CompressionOptions(), password: str | None = None,
                 allow_signed: bool = False, output: str = "") -> None:
        super().__init__()
        self.service, self.action, self.source = service, action, source
        self.options, self.password, self.allow_signed, self.output = options, password, allow_signed, output
        self.cancelled = Event()
        self.signals = CompressionSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.action == "inspect":
                result = self.service.inspect(self.source, self.password)
            elif self.action == "compress":
                result = self.service.compress(self.source, self.options, self.password, self.allow_signed,
                                               self.signals.progress.emit, self.cancelled.is_set)
            else:
                result = self.service.save(self.output, self.signals.progress.emit, self.cancelled.is_set)
            self.signals.succeeded.emit(self.action, result)
        except PasswordRequired:
            self.signals.password_required.emit()
        except Exception as error:
            message = str(error) if isinstance(error, CompressionError) else "Não foi possível concluir a operação. Tente novamente."
            self.signals.failed.emit(message)
        finally:
            self.password = None
            self.signals.finished.emit()
