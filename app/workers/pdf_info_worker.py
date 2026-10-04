"""Execução da leitura fora da thread gráfica."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.pdf_info_service import PdfInfoError, PdfInfoService


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)


class PdfInfoWorker(QRunnable):
    def __init__(self, service: PdfInfoService, path: str) -> None:
        super().__init__()
        self.service = service
        self.path = path
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.service.inspect(self.path)
        except PdfInfoError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            # A fronteira da tarefa evita que falhas encerrem a interface.
            self.signals.failed.emit("Não foi possível analisar o arquivo. Tente outro PDF.")
        else:
            self.signals.succeeded.emit(result)
