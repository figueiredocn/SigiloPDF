from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QComboBox, QFormLayout, QLineEdit, QPushButton, QWidget

from app.services.protection_service import PdfEditError, ProtectionService, validate_password
from app.ui.pages.extract_pdf_page import ExtractPdfPage


class ProtectionPage(ExtractPdfPage):
    service_type = ProtectionService
    page_title = "Proteger PDF"
    suggested_suffix = "_protegido.pdf"
    initial_message = "Selecione um PDF para adicionar ou remover proteção por senha."
    start_message = "Processando a proteção localmente…"

    def __init__(self) -> None:
        super().__init__()
        self.layout().itemAt(4).widget().hide()
        self.expression.hide()
        panel = QWidget()
        form = QFormLayout(panel)
        self.mode = QComboBox()
        self.mode.addItems(("Proteger PDF", "Remover proteção"))
        self.password = QLineEdit()
        self.confirmation = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirmation.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_password = QPushButton("Mostrar senha")
        self.show_password.setCheckable(True)
        self.show_password.toggled.connect(self.toggle_password)
        form.addRow("Ação:", self.mode)
        form.addRow("Senha (nova ou atual):", self.password)
        form.addRow("Confirmar nova senha:", self.confirmation)
        form.addRow(self.show_password)
        self.layout().insertWidget(4, panel)
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.password.textChanged.connect(self.update_summary)
        self.confirmation.textChanged.connect(self.update_summary)
        self.update_summary()

    def toggle_password(self, show: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
        self.password.setEchoMode(mode)
        self.confirmation.setEchoMode(mode)
        self.show_password.setText("Ocultar senha" if show else "Mostrar senha")

    def change_mode(self) -> None:
        self.suggested_suffix = "_desprotegido.pdf" if self.mode.currentIndex() else "_protegido.pdf"
        if self.info is not None:
            source = Path(self.info.path)
            self.output.setText(str(source.with_name(source.stem[:100] + self.suggested_suffix)))
        self.clear_passwords()
        self.update_summary()

    def clear_passwords(self) -> None:
        self.password.setText("")
        self.confirmation.setText("")
        self.show_password.setChecked(False)

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is None:
            self.clear_passwords()
            super().inspect_file(path)

    @Slot(object)
    def show_input(self, info) -> None:
        super().show_input(info)
        self.mode.setCurrentIndex(1 if info.encrypted else 0)
        self.details.setText(f"{info.name} — {info.page_count if info.page_count is not None else 'Páginas protegidas'} — {info.size_bytes} bytes\nCriptografia: {'Sim' if info.encrypted else 'Não'}")

    def update_summary(self, *_args: object) -> None:
        self.summary_valid = False
        if not hasattr(self, "mode") or self.info is None:
            self.summary.setPlainText("Selecione um PDF para configurar a proteção.")
        else:
            try:
                remove = bool(self.mode.currentIndex())
                if remove != self.info.encrypted:
                    raise PdfEditError("Selecione Remover proteção para um PDF protegido, ou Proteger PDF para um documento sem proteção.")
                validate_password(self.password.text(), None if remove else self.confirmation.text())
                self.summary.setPlainText(f"{'A senha atual será validada antes de remover a proteção.' if remove else 'Será aplicada criptografia AES-256.'}\nA senha não será persistida. Guarde-a em local seguro.\nDestino: {self.output.text()}")
                self.summary_valid = True
            except PdfEditError as error:
                self.summary.setPlainText(str(error))
        self.update_controls()

    def update_controls(self) -> None:
        super().update_controls()
        if hasattr(self, "mode"):
            idle = self.worker is None
            for widget in (self.mode, self.password, self.show_password):
                widget.setEnabled(idle)
            self.confirmation.setEnabled(idle and self.mode.currentIndex() == 0)
            self.extract_button.setText(self.mode.currentText())

    @Slot()
    def start_extract(self) -> None:
        if self.worker is None and self.info is not None and self.summary_valid:
            self.service = ProtectionService(self.password.text(), self.confirmation.text(), bool(self.mode.currentIndex()))
            super().start_extract()
            self.clear_passwords()

    @Slot()
    def finish_work(self) -> None:
        self.service.release_secrets()
        super().finish_work()

    @Slot(str)
    def show_success(self, path: str) -> None:
        self.status.setText(f"Operação concluída. Arquivo gerado: {path}")
