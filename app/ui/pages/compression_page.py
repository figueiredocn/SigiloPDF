from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

from app.services.compression_service import (CompressionError, CompressionInput, CompressionMode,
                                              CompressionOptions, CompressionResult, CompressionService,
                                              SIGNATURE_WARNING, describe_result, format_size, parse_target_size)
from app.ui.components.pdf_drop_area import PdfDropArea
from app.ui.pages.reorder_pdf_page import ReorderPdfPage
from app.workers.compression_worker import CompressionWorker


class CompressionPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = CompressionService()
        self.worker: CompressionWorker | None = None
        self.info: CompressionInput | None = None
        self.result: CompressionResult | None = None
        self.source = ""
        self._password: str | None = None
        self.closing = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Comprimir PDF"))
        self.select_button = QPushButton("Selecionar PDF")
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)
        self.drop_area = PdfDropArea()
        self.drop_area.file_dropped.connect(self.inspect_file)
        self.drop_area.invalid_drop.connect(self.show_error)
        layout.addWidget(self.drop_area)
        self.details = QLabel("Selecione um PDF para reduzir seu tamanho.")
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        self._build_options(layout)
        self._build_actions(layout)
        self.update_controls()

    def _build_options(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self.mode = QComboBox()
        for mode in CompressionMode:
            self.mode.addItem(mode.value, mode)
        self.mode.setCurrentIndex(1)
        form.addRow("Modo de compressão:", self.mode)
        self.target_panel = QWidget()
        target_layout = QHBoxLayout(self.target_panel)
        target_layout.setContentsMargins(0, 0, 0, 0)
        self.target = QLineEdit("5")
        self.target.setPlaceholderText("Entre 50 KB e 10 GB")
        self.unit = QComboBox()
        self.unit.addItems(("KB", "MB"))
        self.unit.setCurrentText("MB")
        target_layout.addWidget(self.target)
        target_layout.addWidget(self.unit)
        form.addRow("Tamanho máximo:", self.target_panel)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Senha atual do PDF; usada somente em memória")
        self.unlock_button = QPushButton("Desbloquear PDF")
        self.unlock_button.clicked.connect(self.unlock)
        form.addRow("Senha do PDF:", self.password)
        form.addRow(self.unlock_button)
        layout.addLayout(form)
        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.signature_notice = QLabel(SIGNATURE_WARNING)
        self.signature_notice.setWordWrap(True)
        layout.addWidget(self.signature_notice)
        self.signature = QCheckBox("Estou ciente e desejo continuar com a compressão.")
        layout.addWidget(self.signature)
        self.signature.toggled.connect(self.update_controls)
        self.mode.currentIndexChanged.connect(self.options_changed)
        self.target.textChanged.connect(self.options_changed)
        self.unit.currentIndexChanged.connect(self.options_changed)

    def _build_actions(self, layout: QVBoxLayout) -> None:
        actions = QHBoxLayout()
        self.compress_button = QPushButton("Comprimir PDF")
        self.compress_button.clicked.connect(self.start_compression)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.cancel)
        self.save_button = QPushButton("Salvar arquivo")
        self.save_button.clicked.connect(self.choose_output)
        for button in (self.compress_button, self.cancel_button, self.save_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(180)
        self.results.setPlaceholderText("A comparação será exibida após a compressão.")
        layout.addWidget(self.results)
        layout.addWidget(QLabel("Processamento realizado localmente. Seu arquivo é processado neste computador."))

    def select_file(self) -> None:
        dialog = ReorderPdfPage._dialog(self, False)
        if dialog.exec():
            self.inspect_file(dialog.selectedFiles()[0])

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is not None or self.closing:
            return
        self.clear_result()
        self.info, self.source, self._password = None, path, None
        self.password.clear()
        self.signature.setChecked(False)
        self.password.hide()
        self.unlock_button.hide()
        self.details.setText("Analisando documento…")
        self._launch(CompressionWorker(self.service, "inspect", path))

    def unlock(self) -> None:
        if self.worker is None and self.source:
            self._password = self.password.text()
            self.password.clear()
            self._launch(CompressionWorker(self.service, "inspect", self.source, password=self._password))

    def options_changed(self, *_args: object) -> None:
        if self.worker is None:
            self.clear_result()
        self.update_controls()

    def options(self) -> CompressionOptions:
        mode = self.mode.currentData()
        size = parse_target_size(self.target.text(), self.unit.currentText()) if mode == CompressionMode.TARGET else None
        return CompressionOptions(mode, size)

    def update_controls(self, *_args: object) -> None:
        idle = self.worker is None and not self.closing
        target_mode = self.mode.currentData() == CompressionMode.TARGET
        self.target_panel.setEnabled(idle and target_mode)
        for widget in (self.select_button, self.drop_area, self.mode, self.password, self.unlock_button, self.signature):
            widget.setEnabled(idle)
        self.notice.setText("Tentaremos reduzir o arquivo até o tamanho informado, sem garantir a meta." if target_mode else
                            "Este modo pode reduzir a qualidade de imagens." if self.mode.currentData() == CompressionMode.STRONG else
                            "Texto e vetores são preservados; imagens podem ser recomprimidas.")
        self.signature.setVisible(self.info is not None and self.info.signed)
        self.signature_notice.setVisible(self.info is not None and self.info.signed)
        valid = self.info is not None and (not self.info.signed or self.signature.isChecked())
        try:
            self.options().validate()
        except CompressionError as error:
            valid = False
            self.notice.setText(str(error))
        self.compress_button.setEnabled(idle and valid)
        self.save_button.setEnabled(idle and self.result is not None)
        self.cancel_button.setEnabled(not idle and self.worker is not None and self.worker.action == "compress")

    def start_compression(self) -> None:
        if self.worker is not None or self.info is None or self.closing:
            return
        try:
            options = self.options()
            options.validate()
            password = self._password if self._password is not None else self.password.text() or None
            if self.info.needs_password and password is None:
                raise CompressionError("Informe novamente a senha atual do PDF para comprimir.")
            self._password = None
            self.password.clear()
            self._launch(CompressionWorker(self.service, "compress", self.source, options, password, self.signature.isChecked()))
        except CompressionError as error:
            self.show_error(str(error))

    def choose_output(self) -> None:
        if self.result is None or self.worker is not None:
            return
        dialog = ReorderPdfPage._dialog(self, True)
        dialog.setWindowTitle("Salvar PDF comprimido")
        source = Path(self.source)
        dialog.selectFile(str(source.with_name(source.stem[:100] + "_comprimido.pdf")))
        if dialog.exec():
            self.save_to(dialog.selectedFiles()[0])

    def save_to(self, output: str) -> None:
        if self.worker is None and self.result is not None and not self.closing:
            self._launch(CompressionWorker(self.service, "save", output=output))

    def _launch(self, worker: CompressionWorker) -> None:
        self.worker = worker
        if worker.action == "compress":
            self.result = None
            self.results.clear()
        self.progress.setValue(0)
        self.status.setText("Processando localmente…")
        worker.signals.succeeded.connect(self.succeeded)
        worker.signals.failed.connect(self.show_error)
        worker.signals.password_required.connect(self.password_required)
        worker.signals.progress.connect(self.on_progress)
        worker.signals.finished.connect(self.finished)
        self.update_controls()
        QThreadPool.globalInstance().start(worker)

    @Slot(str, object)
    def succeeded(self, action: str, result: CompressionInput | CompressionResult) -> None:
        if self.closing:
            return
        if isinstance(result, CompressionInput):
            self.info = result
            self.details.setText(f"{result.name}\n{result.page_count} páginas — {format_size(result.size_bytes)}\n"
                                 f"Páginas com imagem predominante: {result.raster_pages}")
            self.password.setVisible(result.encrypted)
            self.unlock_button.hide()
            self.status.setText("PDF carregado. Escolha o modo de compressão.")
        else:
            self.result = result
            self.results.setPlainText(describe_result(result))
            self.status.setText(f"Arquivo salvo: {result.output_path}" if action == "save" else
                                "Compressão concluída. Escolha onde salvar a nova cópia.")

    @Slot()
    def password_required(self) -> None:
        self._password = None
        self.password.show()
        self.unlock_button.show()
        self.show_error("Este PDF está protegido. Informe a senha e clique em Desbloquear PDF.")

    @Slot(int, str)
    def on_progress(self, value: int, message: str) -> None:
        self.progress.setValue(value)
        self.status.setText(message)

    @Slot(str)
    def show_error(self, message: str) -> None:
        self.status.setText(message)
        self._password = None

    @Slot()
    def finished(self) -> None:
        self.worker = None
        if self.closing:
            self.cleanup()
        self.update_controls()

    def cancel(self) -> None:
        if self.worker is not None and self.worker.action == "compress":
            self.worker.cancelled.set()
            self.cancel_button.setEnabled(False)
            self.status.setText("Cancelando após a etapa atual…")

    def clear_result(self) -> None:
        self.result = None
        if not self.service.release_preview():
            self.show_error("O sistema impediu a limpeza dos temporários. Verifique as permissões.")
        self.results.clear()

    def prepare_close(self) -> None:
        self.closing = True
        self.cancel()
        self.password.clear()
        self._password = None

    def cleanup(self) -> None:
        self.clear_result()
        self.password.clear()
        self._password = None
