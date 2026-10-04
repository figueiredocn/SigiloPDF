from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QListWidgetItem, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.services.images_pdf_service import FIT_MODES, IMAGE_SIZE, MARGINS, ORIENTATIONS, ImageInfo, ImagesPdfService
from app.ui.components.image_drop_area import ImageDropArea
from app.ui.components.image_list import ImageList
from app.workers.images_pdf_worker import ImagesWorker


class ImagesPdfPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = ImagesPdfService()
        self.worker: ImagesWorker | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Imagens para PDF"))
        self.select_button = QPushButton("Selecionar imagens")
        self.select_button.clicked.connect(self.select_images)
        layout.addWidget(self.select_button)
        self.drop_area = ImageDropArea()
        self.drop_area.files_dropped.connect(self.add_images)
        self.drop_area.invalid_drop.connect(self.show_error)
        layout.addWidget(self.drop_area)
        self.images = ImageList()
        layout.addWidget(self.images)
        actions = QHBoxLayout()
        self.action_buttons: list[QPushButton] = []
        for text, callback in (("Mover para cima", lambda: self.images.move_selection(-1)),
                               ("Mover para baixo", lambda: self.images.move_selection(1)),
                               ("Remover imagem", self.remove_images), ("Limpar lista", self.clear_images)):
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
            self.action_buttons.append(button)
        layout.addLayout(actions)
        form = QFormLayout()
        self.page_size = self._combo(("A4", "A3", "Carta", IMAGE_SIZE))
        self.orientation = self._combo(ORIENTATIONS)
        self.fit_mode = self._combo(FIT_MODES)
        self.margin = self._combo(tuple(MARGINS))
        self.margin.setCurrentText("Pequena")
        for label, field in (("Tamanho:", self.page_size), ("Orientação:", self.orientation), ("Ajuste:", self.fit_mode), ("Margem:", self.margin)):
            form.addRow(label, field)
        layout.addLayout(form)
        layout.addWidget(QLabel("Preencher página e Tamanho original podem cortar partes da imagem. Transparências usam fundo branco."))
        self.generate_button = QPushButton("Gerar PDF")
        self.generate_button.clicked.connect(self.choose_output)
        self.generate_button.setEnabled(False)
        layout.addWidget(self.generate_button)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.status = QLabel("Adicione imagens para começar.")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.had_error = False

    @staticmethod
    def _combo(values: tuple[str, ...]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(values)
        return combo

    def _dialog(self, saving: bool) -> QFileDialog:
        dialog = QFileDialog(self, "Salvar PDF" if saving else "Selecionar imagens")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)
        dialog.setNameFilter("Arquivos PDF (*.pdf)" if saving else "Imagens (*.jpg *.jpeg *.png *.bmp)")
        dialog.setFileMode(QFileDialog.FileMode.AnyFile if saving else QFileDialog.FileMode.ExistingFiles)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if saving else QFileDialog.AcceptMode.AcceptOpen)
        for label, text in ((QFileDialog.DialogLabel.LookIn, "Examinar:"), (QFileDialog.DialogLabel.FileName, "Nome do arquivo:"),
                            (QFileDialog.DialogLabel.FileType, "Tipo:"), (QFileDialog.DialogLabel.Accept, "Salvar" if saving else "Abrir"),
                            (QFileDialog.DialogLabel.Reject, "Cancelar")):
            dialog.setLabelText(label, text)
        if saving:
            dialog.setDefaultSuffix("pdf")
            dialog.selectFile("imagens_convertidas.pdf")
        return dialog

    def select_images(self) -> None:
        dialog = self._dialog(False)
        if dialog.exec():
            self.add_images(tuple(dialog.selectedFiles()))

    @Slot(object)
    def add_images(self, paths: tuple[str, ...]) -> None:
        if self.worker is None and paths:
            self._launch(ImagesWorker(self.service, tuple(paths)))

    def _launch(self, worker: ImagesWorker) -> None:
        self.worker = worker
        self.had_error = False
        self.progress.setValue(0)
        self.status.setText("Processando localmente…")
        self._set_busy(True)
        worker.signals.inspected.connect(self.inspected)
        worker.signals.failed.connect(self.show_error)
        worker.signals.progress.connect(self.on_progress)
        worker.signals.succeeded.connect(self.succeeded)
        worker.signals.finished.connect(self.finished)
        QThreadPool.globalInstance().start(worker)

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.select_button, self.drop_area, self.images, self.page_size, self.orientation, self.fit_mode, self.margin, *self.action_buttons):
            widget.setEnabled(not busy)
        self.generate_button.setEnabled(not busy and self.images.count() > 0)

    @Slot(object)
    def inspected(self, info: ImageInfo) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(info.thumbnail, "PNG")
        item = QListWidgetItem(QIcon(pixmap), f"{info.path.name}\n{info.width} × {info.height} — {info.size_bytes} bytes")
        # Não conservar uma segunda cópia dos bytes de miniatura.
        item.setData(Qt.ItemDataRole.UserRole, str(info.path))
        self.images.addItem(item)

    @Slot(int, str)
    def on_progress(self, percent: int, text: str) -> None:
        self.progress.setValue(percent)
        if not self.had_error:
            self.status.setText(text)

    @Slot(str)
    def show_error(self, text: str) -> None:
        self.had_error = True
        self.status.setText(text)

    @Slot(str)
    def succeeded(self, output: str) -> None:
        self.status.setText(f"PDF gerado em:\n{output}")

    @Slot()
    def finished(self) -> None:
        self.worker = None
        self._set_busy(False)

    def remove_images(self) -> None:
        self.images.remove_selected()
        self.generate_button.setEnabled(self.images.count() > 0)

    def clear_images(self) -> None:
        self.images.clear()
        self.generate_button.setEnabled(False)

    def choose_output(self) -> None:
        dialog = self._dialog(True)
        if dialog.exec():
            self.generate_to(dialog.selectedFiles()[0])

    def generate_to(self, output: str) -> None:
        if self.worker is not None or self.images.count() == 0:
            return
        paths = tuple(self.images.item(row).data(Qt.ItemDataRole.UserRole) for row in range(self.images.count()))
        settings = (self.page_size.currentText(), self.orientation.currentText(), self.fit_mode.currentText(), self.margin.currentText())
        self._launch(ImagesWorker(self.service, paths, output, settings))
