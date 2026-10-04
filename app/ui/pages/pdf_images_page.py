from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.services.pdf_images_service import JPEG_QUALITIES, RESOLUTIONS, PdfImagesService, PdfInfo
from app.ui.components.page_thumbnail_list import PageThumbnailList
from app.ui.components.pdf_drop_area import PdfDropArea
from app.ui.pages.reorder_pdf_page import ReorderPdfPage
from app.workers.pdf_images_worker import PdfImagesWorker


class PdfImagesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = PdfImagesService()
        self.worker: PdfImagesWorker | None = None
        self.info: PdfInfo | None = None
        self.loaded = 0
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("PDF para imagens"))
        self.select_button = QPushButton("Selecionar PDF")
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)
        self.drop_area = PdfDropArea()
        self.drop_area.file_dropped.connect(self.inspect_file)
        self.drop_area.invalid_drop.connect(self.show_error)
        layout.addWidget(self.drop_area)
        self.details = QLabel("Selecione um PDF para exportar suas páginas.")
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        self.pages = PageThumbnailList()
        self.pages.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.pages.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.pages)
        form = QFormLayout()
        self.selection_mode = QComboBox()
        self.selection_mode.addItems(("Todas as páginas", "Intervalo", "Páginas específicas / combinação"))
        self.expression = QLineEdit()
        self.expression.setPlaceholderText("Exemplos: 1-5 ou 1,3,7 ou 1-3,5,8-10")
        self.image_format = QComboBox()
        self.image_format.addItems(("PNG", "JPEG"))
        self.resolution = QComboBox()
        self.resolution.addItems(tuple(f"{value} DPI" for value in RESOLUTIONS))
        self.resolution.setCurrentText("150 DPI")
        self.quality = QComboBox()
        self.quality.addItems(tuple(JPEG_QUALITIES))
        self.quality.setCurrentText("Alta")
        for label, field in (("Páginas:", self.selection_mode), ("Seleção:", self.expression), ("Formato:", self.image_format), ("Resolução:", self.resolution), ("Qualidade JPEG:", self.quality)):
            form.addRow(label, field)
        layout.addLayout(form)
        self.selection_mode.currentIndexChanged.connect(self.update_options)
        self.image_format.currentIndexChanged.connect(self.update_options)
        destination = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        self.folder.setPlaceholderText("Escolha uma pasta local de saída")
        self.folder_button = QPushButton("Escolher pasta")
        self.folder_button.clicked.connect(self.choose_folder)
        destination.addWidget(self.folder)
        destination.addWidget(self.folder_button)
        layout.addLayout(destination)
        buttons = QHBoxLayout()
        self.export_button = QPushButton("Exportar imagens")
        self.export_button.clicked.connect(self.start_export)
        self.cancel_button = QPushButton("Cancelar exportação")
        self.cancel_button.clicked.connect(self.cancel)
        self.cancel_button.setEnabled(False)
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Os caminhos das imagens geradas serão exibidos aqui.")
        self.results.setMaximumHeight(120)
        layout.addWidget(self.results)
        self.update_options()

    def select_file(self) -> None:
        dialog = ReorderPdfPage._dialog(self, False)
        if dialog.exec():
            self.inspect_file(dialog.selectedFiles()[0])

    def choose_folder(self) -> None:
        dialog = ReorderPdfPage._dialog(self, False)
        dialog.setWindowTitle("Escolher pasta de saída")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly)
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Escolher")
        dialog.setNameFilter("Pastas (*)")
        if dialog.exec():
            self.folder.setText(dialog.selectedFiles()[0])
            self.update_options()

    def update_options(self) -> None:
        busy = self.worker is not None
        self.expression.setEnabled(not busy and self.selection_mode.currentIndex() != 0)
        self.quality.setEnabled(not busy and self.image_format.currentText() == "JPEG")
        self.export_button.setEnabled(not busy and self.info is not None and bool(self.folder.text()))

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is not None:
            return
        self.info, self.loaded = None, 0
        self.pages.clear()
        self.results.clear()
        self.details.setText("Verificando o PDF…")
        self._launch(PdfImagesWorker(self.service, path))

    def _launch(self, worker: PdfImagesWorker) -> None:
        self.worker = worker
        self.progress.setValue(0)
        self.status.setText("Processando localmente…")
        for widget in (self.select_button, self.drop_area, self.selection_mode, self.image_format, self.resolution, self.folder_button):
            widget.setEnabled(False)
        self.cancel_button.setEnabled(worker.folder is not None)
        self.update_options()
        worker.signals.inspected.connect(self.inspected)
        worker.signals.thumbnail.connect(self.thumbnail)
        worker.signals.progress.connect(self.on_progress)
        worker.signals.failed.connect(self.show_error)
        worker.signals.succeeded.connect(self.succeeded)
        worker.signals.finished.connect(self.finished)
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def inspected(self, info: PdfInfo) -> None:
        self.info = info
        self.details.setText(f"{info.name} — {info.page_count} páginas — {info.size_bytes} bytes")
        self.pages.populate(info.page_count or 0)

    @Slot(int, bytes)
    def thumbnail(self, index: int, data: bytes) -> None:
        self.pages.thumbnail(index, data)
        self.loaded += 1
        self.on_progress(int(100 * self.loaded / self.pages.count()), f"{self.loaded} / {self.pages.count()} miniaturas carregadas")

    @Slot(int, str)
    def on_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.status.setText(message)

    @Slot(str)
    def show_error(self, message: str) -> None:
        self.status.setText(message)

    @Slot(object)
    def succeeded(self, files: list[Path]) -> None:
        self.status.setText(f"Exportação concluída. {len(files)} imagens geradas.")
        self.results.setPlainText("\n".join(str(path) for path in files))

    @Slot()
    def finished(self) -> None:
        self.worker = None
        for widget in (self.select_button, self.drop_area, self.selection_mode, self.image_format, self.resolution, self.folder_button):
            widget.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.update_options()

    def start_export(self) -> None:
        if self.worker is not None or self.info is None:
            return
        self.results.clear()
        expression = None if self.selection_mode.currentIndex() == 0 else self.expression.text()
        worker = PdfImagesWorker(self.service, str(self.info.path), self.folder.text(), expression,
                                 self.image_format.currentText(), RESOLUTIONS[self.resolution.currentIndex()],
                                 JPEG_QUALITIES[self.quality.currentText()])
        self._launch(worker)

    def cancel(self) -> None:
        if self.worker is not None:
            self.worker.cancelled.set()
            self.cancel_button.setEnabled(False)
            self.status.setText("Cancelando após a página atual…")

    def prepare_close(self) -> None:
        if self.worker is not None:
            self.worker.cancelled.set()
