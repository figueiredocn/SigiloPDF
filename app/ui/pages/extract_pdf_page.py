from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.services.extract_pdf_service import ExtractPdfError, ExtractPdfService, PdfInfo
from app.ui.components.pdf_drop_area import PdfDropArea
from app.workers.extract_pdf_worker import ExtractPdfWorker, InspectExtractWorker


class ExtractPdfPage(QWidget):
    service_type = ExtractPdfService
    page_title = "Extrair páginas"
    selection_caption = "Páginas desejadas"
    summary_caption = "Resumo antes de processar — ordem informada, sem páginas repetidas"
    suggested_suffix = "_extraido.pdf"
    initial_message = "Selecione um PDF e informe as páginas desejadas."
    start_message = "Iniciando a extração local…"

    def __init__(self) -> None:
        super().__init__()
        self.service = self.service_type()
        self.info: PdfInfo | None = None
        self.worker: InspectExtractWorker | ExtractPdfWorker | None = None
        self.summary_valid = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.page_title))
        self.select_button = QPushButton("Selecionar PDF")
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)
        self.drop_area = PdfDropArea()
        self.drop_area.file_dropped.connect(self.inspect_file)
        self.drop_area.invalid_drop.connect(self.show_invalid_drop)
        layout.addWidget(self.drop_area)
        self.details = QLabel("Nenhum PDF selecionado.")
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        layout.addWidget(QLabel(self.selection_caption))
        self.expression = QLineEdit()
        self.expression.setPlaceholderText("Exemplos: 1 · 1,3,5 · 1-5 · 1-3,6,10-14")
        layout.addWidget(self.expression)
        layout.addWidget(QLabel(self.summary_caption))
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)
        output_layout = QHBoxLayout()
        self.output = QLineEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Escolha o arquivo de destino")
        self.output_button = QPushButton("Escolher destino")
        self.output_button.clicked.connect(self.select_output)
        output_layout.addWidget(self.output)
        output_layout.addWidget(self.output_button)
        layout.addLayout(output_layout)
        layout.addWidget(QLabel("O original é preservado. Nomes existentes recebem _2, _3…"))
        self.extract_button = QPushButton(self.page_title)
        self.extract_button.clicked.connect(self.start_extract)
        layout.addWidget(self.extract_button)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.status = QLabel(self.initial_message)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.expression.textChanged.connect(self.update_summary)
        self.output.textChanged.connect(self.update_summary)
        self.update_summary()

    def file_dialog(self, save: bool) -> QFileDialog:
        dialog = QFileDialog(self, "Escolher destino" if save else "Selecionar PDF")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setNameFilter("Arquivos PDF (*.pdf *.PDF)")
        dialog.setFileMode(QFileDialog.FileMode.AnyFile if save else QFileDialog.FileMode.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if save else QFileDialog.AcceptMode.AcceptOpen)
        if save:
            dialog.setDefaultSuffix("pdf")
            dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)
            if self.output.text():
                dialog.selectFile(self.output.text())
        labels = {
            QFileDialog.DialogLabel.LookIn: "Examinar:",
            QFileDialog.DialogLabel.FileName: "Nome do arquivo:",
            QFileDialog.DialogLabel.FileType: "Tipo de arquivo:",
            QFileDialog.DialogLabel.Accept: "Escolher" if save else "Abrir",
            QFileDialog.DialogLabel.Reject: "Cancelar",
        }
        for label, text in labels.items():
            dialog.setLabelText(label, text)
        return dialog

    @Slot()
    def select_file(self) -> None:
        dialog = self.file_dialog(False)
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            self.inspect_file(dialog.selectedFiles()[0])

    @Slot()
    def select_output(self) -> None:
        dialog = self.file_dialog(True)
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            self.output.setText(dialog.selectedFiles()[0])

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is not None:
            return
        self.info = None
        self.details.setText("Verificando o PDF…")
        self.output.clear()
        self.progress.setRange(0, 0)
        self.worker = InspectExtractWorker(self.service, path)
        self.worker.signals.inspected.connect(self.show_input)
        self.connect_worker()
        self.status.setText("Verificando o PDF localmente…")
        QThreadPool.globalInstance().start(self.worker)

    @Slot(object)
    def show_input(self, info: PdfInfo) -> None:
        self.info = info
        self.details.setText(f"{info.name} — Total: {info.page_count} página(s)")
        source = Path(info.path)
        self.output.setText(str(source.with_name(source.stem[:100] + self.suggested_suffix)))
        self.status.setText("Confira o resumo e o destino antes de processar.")

    def update_summary(self, *_args: object) -> None:
        self.summary_valid = False
        if self.info is None:
            self.summary.setPlainText("Selecione um PDF para visualizar o resumo.")
        else:
            try:
                summary = self.service.summarize(self.expression.text(), self.info.page_count or 0)
                order = ", ".join(str(page) for page in summary.pages)
                self.summary.setPlainText(f"{len(summary.pages)} página(s) selecionada(s).\nOrdem de extração: {order}\nDestino sugerido: {self.output.text()}\nSe existir, será usado um nome com sufixo numérico.")
                self.summary_valid = True
            except ExtractPdfError as error:
                self.summary.setPlainText(str(error))
        self.update_controls()

    def connect_worker(self) -> None:
        if self.worker is not None:
            self.worker.signals.failed.connect(self.show_error)
            self.worker.signals.finished.connect(self.finish_work)
        self.update_controls()

    @Slot()
    def start_extract(self) -> None:
        if self.worker is not None or self.info is None or not self.summary_valid or not self.output.text():
            return
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.worker = ExtractPdfWorker(self.service, self.info.path, self.output.text(), self.expression.text())
        self.worker.signals.progress.connect(self.show_progress)
        self.worker.signals.succeeded.connect(self.show_success)
        self.connect_worker()
        self.status.setText(self.start_message)
        QThreadPool.globalInstance().start(self.worker)

    @Slot(int, str)
    def show_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.status.setText(message)

    @Slot(str)
    def show_success(self, path: str) -> None:
        self.status.setText(f"Extração concluída. Arquivo gerado: {path}")

    @Slot(str)
    def show_error(self, message: str) -> None:
        self.status.setText(message)
        if self.info is None:
            self.details.setText("Nenhum PDF selecionado.")

    @Slot(str)
    def show_invalid_drop(self, message: str) -> None:
        if self.worker is None:
            self.status.setText(message)

    @Slot()
    def finish_work(self) -> None:
        if isinstance(self.worker, InspectExtractWorker):
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
        self.worker = None
        self.update_summary()

    def update_controls(self) -> None:
        idle = self.worker is None
        for widget in (self.select_button, self.drop_area, self.expression, self.output_button):
            widget.setEnabled(idle)
        self.extract_button.setEnabled(idle and self.info is not None and self.summary_valid and bool(self.output.text()))
