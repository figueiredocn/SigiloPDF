"""Sobre o aplicativo e mensagem especial acessível pelo logotipo."""

from importlib.metadata import PackageNotFoundError, version

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextEdit, QVBoxLayout
from app.ui.branding import BrandHeader, brand_icon

MESSAGE = """Nem todo documento deveria precisar passar pela internet para que uma tarefa simples pudesse ser realizada.

O SigiloPDF nasceu de uma ideia simples: devolver ao usuário o controle sobre seus próprios arquivos.

Contratos, trabalhos acadêmicos, documentos pessoais, relatórios, processos e tantas outras informações podem conter dados que pertencem somente a quem os possui.

Por isso este projeto foi desenvolvido para trabalhar localmente, sem exigir que seus documentos sejam enviados para um servidor apenas para juntar páginas, reorganizar um arquivo ou realizar outras operações básicas.

Mais do que criar uma ferramenta de PDF, queremos mostrar que privacidade também pode ser simples, acessível e gratuita.

Obrigado por escolher o SigiloPDF e por confiar neste projeto.

Espero que ele seja útil para você.

— Desenvolvedor do SigiloPDF"""


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sobre o SigiloPDF")
        self.setWindowIcon(brand_icon())
        self.resize(440, 320)
        self._logo_clicks = 0
        self.special_dialog: QDialog | None = None
        layout = QVBoxLayout(self)
        self.logo = QPushButton("SigiloPDF")
        self.logo.setObjectName("brandLogo")
        self.logo.setAccessibleName("Logotipo do SigiloPDF")
        self.logo.setIcon(brand_icon("simbolo-claro.svg"))
        self.logo.setIconSize(QSize(64, 64))
        self.logo.clicked.connect(self._logo_clicked)
        self._secret_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        self._secret_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._secret_shortcut.activated.connect(self.show_special)
        layout.addWidget(self.logo)
        layout.addWidget(QLabel("Seus documentos. Seu computador. Seu controle."))
        description = QLabel("Toolkit open source para manipulação local de arquivos PDF.")
        description.setWordWrap(True)
        layout.addWidget(description)
        try:
            release = version("sigilopdf")
        except PackageNotFoundError:
            release = "1.0.0"
        layout.addWidget(QLabel(f"Versão: {release}\nLicença do projeto: MIT\nSeus arquivos são processados localmente."))
        close = QPushButton("Fechar")
        close.clicked.connect(self.close)
        layout.addWidget(close)
        # Qualquer clique fora do logotipo interrompe a sequência, inclusive em filhos.
        self.installEventFilter(self)
        for widget in self.findChildren(QLabel) + self.findChildren(QPushButton):
            widget.installEventFilter(self)

    def _logo_clicked(self) -> None:
        self._logo_clicks += 1
        if self._logo_clicks != 5:
            return
        self.show_special()

    def show_special(self) -> None:
        self._logo_clicks = 0
        if self.special_dialog is not None and self.special_dialog.isVisible():
            self.special_dialog.raise_()
            self.special_dialog.activateWindow()
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Por que criamos o SigiloPDF?")
        dialog.setWindowIcon(brand_icon())
        dialog.resize(560, 540)
        layout = QVBoxLayout(dialog)
        layout.addWidget(BrandHeader())
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(MESSAGE)
        layout.addWidget(text)
        slogan = QLabel("Seus documentos. Seu computador. Seu controle.")
        slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(slogan)
        close = QPushButton("Fechar")
        close.clicked.connect(dialog.close)
        layout.addWidget(close)
        self.special_dialog = dialog
        dialog.setModal(True)
        dialog.show()

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
            if watched is self.logo and event.button() == Qt.MouseButton.LeftButton:
                # Contar também os duplos cliques rápidos; não depender de clicked(),
                # que só é emitido após a liberação aceita pelo botão.
                self._logo_clicked()
                return True
            self._logo_clicks = 0
        return super().eventFilter(watched, event)
