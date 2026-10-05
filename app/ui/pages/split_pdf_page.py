from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.services.split_pdf_service import PdfInfo, SplitMode, SplitPdfService
from app.ui.components.pdf_drop_area import PdfDropArea
from app.ui.components.page_preview_panel import PagePreviewPanel
from app.workers.split_pdf_worker import InspectSplitWorker, SplitPdfWorker


class SplitPdfPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = SplitPdfService()
        self.worker: InspectSplitWorker | SplitPdfWorker | None = None
        self.info: PdfInfo | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Dividir PDF"))
        self.select_button = QPushButton("Selecionar PDF")
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)
        self.drop_area = PdfDropArea()
        self.drop_area.file_dropped.connect(self.inspect_file)
        self.drop_area.invalid_drop.connect(self.show_invalid_drop)
        layout.addWidget(self.drop_area)
        self.file_details = QLabel("Nenhum PDF selecionado.")
        self.file_details.setTextFormat(Qt.TextFormat.PlainText)
        self.file_details.setWordWrap(True)
        layout.addWidget(self.file_details)
        self.mode = QComboBox()
        for label, mode in [("Cada página em um PDF", SplitMode.EACH_PAGE), ("Intervalo", SplitMode.RANGE), ("Páginas específicas", SplitMode.SPECIFIC), ("Combinação", SplitMode.COMBINATION), ("Pontos de divisão (após páginas)", SplitMode.POINTS)]:
            self.mode.addItem(label, mode)
        self.mode.currentIndexChanged.connect(self.update_mode)
        layout.addWidget(QLabel("Modo de divisão"))
        layout.addWidget(self.mode)
        self.expression = QLineEdit()
        self.expression.textChanged.connect(self.update_controls)
        layout.addWidget(self.expression)
        layout.addWidget(QLabel("Páginas repetidas são removidas. A saída segue a ordem crescente das páginas."))
        folder_layout = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        self.folder.setPlaceholderText("Escolha uma pasta de saída")
        self.folder.textChanged.connect(self.update_controls)
        self.folder_button = QPushButton("Escolher pasta de saída")
        self.folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder)
        folder_layout.addWidget(self.folder_button)
        layout.addLayout(folder_layout)
        layout.addWidget(QLabel("Arquivos existentes são preservados; nomes em conflito recebem _2, _3…"))
        self.split_button = QPushButton("Dividir PDF")
        self.split_button.clicked.connect(self.start_split)
        layout.addWidget(self.split_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status = QLabel("Selecione um PDF para começar.")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(QLabel("Arquivos gerados"))
        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        layout.addWidget(self.results)
        self.update_mode()
        self.preview = PagePreviewPanel(self)
        self.preview.bind(self.expression, self.choose_visual_mode)
        layout.addWidget(self.preview)
        self.mark_button = QPushButton("Marcar divisão após páginas selecionadas")
        self.mark_button.clicked.connect(self.mark_points)
        layout.addWidget(self.mark_button)

    def choose_visual_mode(self) -> None:
        if self.mode.currentData() != SplitMode.POINTS:
            self.mode.setCurrentIndex(3)

    def mark_points(self) -> None:
        indices = self.preview.pages.selected_pages()
        self.mode.setCurrentIndex(self.mode.findData(SplitMode.POINTS))
        self.expression.setText(self.preview.service.expression(indices))

    def file_dialog(self, directory: bool) -> QFileDialog:
        dialog = QFileDialog(self, "Escolher pasta de saída" if directory else "Selecionar PDF")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setFileMode(QFileDialog.FileMode.Directory if directory else QFileDialog.FileMode.ExistingFile)
        if directory:
            dialog.setOption(QFileDialog.Option.ShowDirsOnly)
        else:
            dialog.setNameFilter("Arquivos PDF (*.pdf *.PDF)")
        labels = {
            QFileDialog.DialogLabel.LookIn: "Examinar:",
            QFileDialog.DialogLabel.FileName: "Pasta:" if directory else "Nome do arquivo:",
            QFileDialog.DialogLabel.FileType: "Tipo de arquivo:",
            QFileDialog.DialogLabel.Accept: "Escolher" if directory else "Abrir",
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
    def select_folder(self) -> None:
        dialog = self.file_dialog(True)
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            self.folder.setText(dialog.selectedFiles()[0])

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is not None:
            return
        self.info = None
        self.preview.reset()
        self.file_details.setText("Verificando o PDF…")
        self.results.clear()
        self.progress.setRange(0, 0)
        self.worker = InspectSplitWorker(self.service, path)
        self.worker.signals.inspected.connect(self.show_input)
        self.connect_worker()
        self.status.setText("Verificando o PDF localmente…")
        QThreadPool.globalInstance().start(self.worker)

    @Slot(object)
    def show_input(self, info: PdfInfo) -> None:
        self.info = info
        size = f"{info.size_bytes:,}".replace(",", ".")
        self.file_details.setText(f"{info.name}\nTotal: {info.page_count} página(s) — Tamanho: {size} bytes")
        self.file_details.setToolTip(info.path)
        self.status.setText("PDF carregado. Escolha o modo e a pasta de saída.")
        self.preview.load(info.path, info.page_count or 0)

    def connect_worker(self) -> None:
        if self.worker is None:
            return
        self.worker.signals.failed.connect(self.show_error)
        self.worker.signals.finished.connect(self.finish_work)
        self.update_controls()

    @Slot()
    def start_split(self) -> None:
        if self.worker is not None or self.info is None or not self.folder.text():
            return
        self.results.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.worker = SplitPdfWorker(self.service, self.info.path, self.folder.text(), SplitMode(self.mode.currentData()), self.expression.text())
        self.worker.signals.progress.connect(self.show_progress)
        self.worker.signals.succeeded.connect(self.show_results)
        self.connect_worker()
        self.status.setText("Iniciando a divisão local…")
        QThreadPool.globalInstance().start(self.worker)

    @Slot(int, str)
    def show_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.status.setText(message)

    @Slot(list)
    def show_results(self, paths: list[str]) -> None:
        self.results.setPlainText("\n".join(paths))
        self.status.setText(f"Divisão concluída. {len(paths)} arquivo(s) gerado(s). Os caminhos estão abaixo.")

    @Slot(str)
    def show_error(self, message: str) -> None:
        self.status.setText(message)
        if self.info is None:
            self.file_details.setText("Nenhum PDF selecionado.")

    @Slot(str)
    def show_invalid_drop(self, message: str) -> None:
        if self.worker is None:
            self.status.setText(message)

    @Slot()
    def finish_work(self) -> None:
        if isinstance(self.worker, InspectSplitWorker):
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
        self.worker = None
        self.update_controls()

    def update_mode(self, *_args: object) -> None:
        hints = {
            SplitMode.EACH_PAGE: "Não é necessário informar páginas neste modo",
            SplitMode.RANGE: "Exemplo: 1-5",
            SplitMode.SPECIFIC: "Exemplo: 1,3,5,8",
            SplitMode.COMBINATION: "Exemplo: 1-3,5,8-10",
            SplitMode.POINTS: "Exemplo: 2,5 — criar partes 1-2, 3-5 e 6-final",
        }
        self.expression.setPlaceholderText(hints[SplitMode(self.mode.currentData())])
        self.update_controls()

    def update_controls(self, *_args: object) -> None:
        idle = self.worker is None
        each_page = self.mode.currentData() == SplitMode.EACH_PAGE
        for widget in (self.select_button, self.drop_area, self.mode, self.folder_button):
            widget.setEnabled(idle)
        self.expression.setEnabled(idle and not each_page)
        self.split_button.setEnabled(idle and self.info is not None and bool(self.folder.text()) and (each_page or bool(self.expression.text().strip())))
        if hasattr(self, "preview"):
            self.preview.setEnabled(idle)
            self.mark_button.setEnabled(idle and self.info is not None)
            if each_page:
                self.preview.pages.select_pages(tuple(range(self.preview.pages.count())))
            if self.mode.currentData() == SplitMode.POINTS:
                try:
                    points = self.preview.service.selection(self.expression.text(), self.preview.pages.count())
                except ValueError:
                    points = ()
                self.preview.pages.set_split_points(points)
            else:
                self.preview.pages.set_split_points(())
