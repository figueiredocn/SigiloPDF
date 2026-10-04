from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.images_pdf_service import ImagesPdfError, ImagesPdfService


class ImagesSignals(QObject):
    inspected = Signal(object)
    progress = Signal(int, str)
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class ImagesWorker(QRunnable):
    def __init__(self, service: ImagesPdfService, paths: tuple[str, ...], output: str = "",
                 settings: tuple[str, str, str, str] = ("A4", "Automática", "Ajustar à página", "Pequena")) -> None:
        super().__init__()
        self.service, self.paths, self.output, self.settings = service, paths, output, settings
        self.signals = ImagesSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.output:
                result = self.service.generate(self.paths, self.output, self.settings, self.signals.progress.emit)
                self.signals.succeeded.emit(str(result))
            else:
                for index, path in enumerate(self.paths):
                    try:
                        self.signals.inspected.emit(self.service.inspect(path))
                    except ImagesPdfError as error:
                        self.signals.failed.emit(str(error))
                    self.signals.progress.emit(int(100 * (index + 1) / len(self.paths)), f"Verificando imagem {index + 1} de {len(self.paths)}…")
        except ImagesPdfError as error:
            self.signals.failed.emit(str(error))
        except Exception:
            self.signals.failed.emit("Não foi possível concluir a operação. Tente novamente.")
        finally:
            self.signals.finished.emit()
