import time

from PySide6.QtCore import QObject, QThreadPool, QTimer, Slot
from PySide6.QtWidgets import QMainWindow

from app.services.update_preferences import UpdatePreferenceStore
from app.services.update_service import UpdateInfo, UpdateService
from app.ui.components.update_dialog import UpdateDialog
from app.workers.update_worker import UpdateWorker


class UpdateController(QObject):
    def __init__(self, window: QMainWindow, store: UpdatePreferenceStore | None = None,
                 service: UpdateService | None = None) -> None:
        super().__init__(window)
        self.window = window
        self.store = store or UpdatePreferenceStore()
        self.preferences = self.store.load()
        self.service = service or UpdateService()
        self.worker: UpdateWorker | None = None
        self.dialog: UpdateDialog | None = None
        self.info: UpdateInfo | None = None
        self.closing, self.manual = False, False
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.timer = QTimer(self)
        self.timer.setInterval(3600000)
        self.timer.timeout.connect(self.check_automatic)
        self.timer.start()
        QTimer.singleShot(2000, self, self.check_automatic)

    def save_preferences(self) -> bool:
        try:
            self.store.save(self.preferences)
            return True
        except OSError:
            if self.dialog is not None:
                self.dialog.status.setText("Não foi possível salvar a preferência de atualização.")
            return False

    @Slot(bool)
    def set_automatic(self, automatic: bool) -> None:
        previous = self.preferences.automatic
        self.preferences.automatic = automatic
        if not self.save_preferences():
            self.preferences.automatic = previous
        if self.dialog is not None:
            self.dialog.automatic.blockSignals(True)
            self.dialog.automatic.setChecked(self.preferences.automatic)
            self.dialog.automatic.blockSignals(False)

    @Slot()
    def show_dialog(self) -> None:
        if self.closing:
            return
        if self.dialog is None:
            self.dialog = UpdateDialog(self.preferences.automatic, self.window)
            self.dialog.check_requested.connect(self.check_manual)
            self.dialog.automatic_changed.connect(self.set_automatic)
        if self.info is not None:
            self.dialog.show_result(self.info)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    @Slot()
    def check_manual(self) -> None:
        self.check(True)

    @Slot()
    def check_automatic(self) -> None:
        if self.preferences.due(time.time()):
            self.check(False)

    def check(self, manual: bool) -> None:
        if self.closing:
            return
        if manual:
            self.show_dialog()
        if self.worker is not None:
            self.manual = self.manual or manual
            return
        self.manual = manual
        self.preferences.last_check = time.time()
        if not self.save_preferences() and not manual:
            return
        if manual and self.dialog is not None:
            self.dialog.status.setText("Verificando releases públicas do SigiloPDF…")
            self.dialog.check.setEnabled(False)
        self.worker = UpdateWorker(self.service)
        self.worker.signals.result.connect(self.received)
        self.pool.start(self.worker)

    @Slot(object)
    def received(self, info: UpdateInfo) -> None:
        self.worker = None
        if self.closing:
            return
        self.info = info
        if info.latest_version:
            self.preferences.latest_version = info.latest_version
            self.save_preferences()
        if self.manual:
            self.show_dialog()
        if self.dialog is not None:
            self.dialog.show_result(info)
        if info.update_available and not self.manual:
            self.window.statusBar().showMessage("Uma nova versão do SigiloPDF está disponível. Veja Ajuda → Verificar atualizações.")

    def prepare_close(self) -> None:
        self.closing = True
        self.timer.stop()
        if self.dialog is not None:
            self.dialog.close()

    def pending(self) -> bool:
        return self.worker is not None or self.pool.activeThreadCount() > 0
