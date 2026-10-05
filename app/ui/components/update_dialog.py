from PySide6.QtCore import Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.services.update_service import UpdateInfo, UpdateState
from app.ui.branding import brand_icon
from app.version import __version__


class UpdateDialog(QDialog):
    check_requested = Signal()
    automatic_changed = Signal(bool)

    def __init__(self, automatic: bool, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Atualizações do SigiloPDF")
        self.setWindowIcon(brand_icon())
        self.resize(520, 430)
        self.info: UpdateInfo | None = None
        layout = QVBoxLayout(self)
        self.status = QLabel(f"Versão instalada: {__version__}")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.automatic = QCheckBox("Verificar automaticamente se existem novas versões")
        self.automatic.setChecked(automatic)
        self.automatic.toggled.connect(self.automatic_changed)
        layout.addWidget(self.automatic)
        explanation = QLabel("O SigiloPDF consulta a página pública de releases do projeto. Nenhum documento ou informação sobre os seus arquivos é enviado. A consulta automática é opcional, no máximo uma vez a cada 24 horas.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.hide()
        layout.addWidget(self.notes)
        actions = QHBoxLayout()
        self.check = QPushButton("Verificar agora")
        self.check.clicked.connect(self.check_requested)
        self.news = QPushButton("Ver novidades")
        self.news.clicked.connect(lambda: self.notes.setVisible(not self.notes.isVisible()))
        self.download = QPushButton("Baixar atualização")
        self.download.clicked.connect(self.open_release)
        self.news.hide()
        self.download.hide()
        close = QPushButton("Agora não")
        close.clicked.connect(self.close)
        for button in (self.check, self.news, self.download, close):
            actions.addWidget(button)
        layout.addLayout(actions)

    def show_result(self, info: UpdateInfo) -> None:
        self.info = info
        messages = {
            UpdateState.UP_TO_DATE: "Você está usando a versão mais recente do SigiloPDF.",
            UpdateState.UPDATE_AVAILABLE: "Uma nova versão do SigiloPDF está disponível.",
            UpdateState.DEV_VERSION: "Esta versão é mais recente que a última release pública.",
            UpdateState.CHECK_FAILED: "Não foi possível verificar atualizações agora.",
        }
        latest = f"\nVersão pública: {info.latest_version}" if info.latest_version else ""
        self.status.setText(f"{messages[info.state]}\nVersão instalada: {info.current_version}{latest}")
        self.check.setEnabled(True)
        self.news.setVisible(info.update_available)
        self.download.setVisible(info.update_available)
        self.notes.setPlainText(info.release_notes)

    def open_release(self) -> None:
        if self.info is not None and self.info.update_available:
            QDesktopServices.openUrl(QUrl(self.info.release_url))
