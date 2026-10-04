from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.merge_pdf_service import MergePdfError, MergePdfService


class MergeSignals(QObject):
    inspected = Signal(object)
    progress = Signal(int, str)
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class InspectMergeWorker(QRunnable):
    def __init__(self, service: MergePdfService, paths: list[str]) -> None:
        super().__init__()
        self.service = service
        self.paths = paths
        self.signals = MergeSignals()

    @Slot()
    def run(self) -> None:
        try:
            for index, path in enumerate(self.paths):
                try:
                    self.signals.inspected.emit(self.service.inspect(path))
                except MergePdfError as error:
                    self.signals.failed.emit(str(error))
                self.signals.progress.emit(int(100 * (index + 1) / len(self.paths)), "Verificando os arquivos adicionados…")
        except Exception:
            self.signals.failed.emit("Não foi possível verificar os arquivos. Tente novamente.")
        finally:
            self.signals.finished.emit()


class MergePdfWorker(QRunnable):
    def __init__(self, service: MergePdfService, paths: list[str], output: str) -> None:
        super().__init__()
        self.service = service
        self.paths = paths
        self.output = output
        self.signals = MergeSignals()

    @Slot()
    def run(self) -> None:
        try:
            path = self.service.merge(self.paths, self.output, self.signals.progress.emit)
            self.signals.succeeded.emit(str(path))
        except MergePdfError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            self.signals.failed.emit("Não foi possível concluir a junção. Tente novamente.")
        finally:
            self.signals.finished.emit()
