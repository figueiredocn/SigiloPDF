from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.services.update_service import UpdateInfo, UpdateService, UpdateState


class UpdateSignals(QObject):
    result = Signal(object)


class UpdateWorker(QRunnable):
    def __init__(self, service: UpdateService) -> None:
        super().__init__()
        self.service = service
        self.signals = UpdateSignals()

    @Slot()
    def run(self) -> None:
        try:
            info = self.service.check()
        except Exception:
            info = UpdateInfo(self.service.current_version, UpdateState.CHECK_FAILED)
        self.signals.result.emit(info)
