from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.services.reorder_pdf_service import PdfInfo, ReorderPdfService
from app.ui.components.page_preview_panel import PagePreviewPanel
from app.ui.components.pdf_drop_area import PdfDropArea
from app.workers.reorder_pdf_worker import ReorderWorker


class ReorderPdfPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = ReorderPdfService()
        self.worker: ReorderWorker | None = None
        self.pending_workers: set[ReorderWorker] = set()
        self.info: PdfInfo | None = None
        self.loaded = 0
        self.failed = False
        self._generation = 0
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Organizar páginas"))
        self.select_button = QPushButton("Selecionar PDF")
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)
        self.drop_area = PdfDropArea()
        self.drop_area.file_dropped.connect(self.inspect_file)
        self.drop_area.invalid_drop.connect(self.show_error)
        layout.addWidget(self.drop_area)
        self.details = QLabel("Selecione um PDF para organizar suas páginas.")
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        layout.addWidget(QLabel("Arraste as páginas para alterar a ordem. Use Ctrl ou Shift para selecionar várias."))
        self.preview = PagePreviewPanel(self, reorder=True)
        self.pages = self.preview.pages
        self.pages.order_changed.connect(self.update_modified)
        layout.addWidget(self.preview)
        actions = QHBoxLayout()
        self.start_button = QPushButton("Mover para o início")
        self.end_button = QPushButton("Mover para o fim")
        self.restore_button = QPushButton("Restaurar ordem original")
        self.left_button = QPushButton("←")
        self.right_button = QPushButton("→")
        self.left_button.setToolTip("Mover página para a esquerda (Alt+←)")
        self.right_button.setToolTip("Mover página para a direita (Alt+→)")
        self.left_button.setAccessibleName("Mover página para a esquerda")
        self.right_button.setAccessibleName("Mover página para a direita")
        self.left_button.clicked.connect(lambda: self.pages.move_step(-1))
        self.right_button.clicked.connect(lambda: self.pages.move_step(1))
        self.start_button.clicked.connect(lambda: self.pages.move_selected(True))
        self.end_button.clicked.connect(lambda: self.pages.move_selected(False))
        self.restore_button.clicked.connect(self.restore_order)
        for button in (self.left_button, self.right_button, self.start_button, self.end_button, self.restore_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.modified = QLabel("")
        layout.addWidget(self.modified)
        self.save_button = QPushButton("Salvar PDF reorganizado")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.choose_output)
        layout.addWidget(self.save_button)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)

    def _dialog(self, saving: bool) -> QFileDialog:
        dialog = QFileDialog(self, "Salvar PDF reorganizado" if saving else "Selecionar PDF")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)
        dialog.setNameFilter("Arquivos PDF (*.pdf)")
        dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "Examinar:")
        dialog.setLabelText(QFileDialog.DialogLabel.FileName, "Nome do arquivo:")
        dialog.setLabelText(QFileDialog.DialogLabel.FileType, "Tipo:")
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Salvar" if saving else "Abrir")
        dialog.setLabelText(QFileDialog.DialogLabel.Reject, "Cancelar")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if saving else QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile if saving else QFileDialog.FileMode.ExistingFile)
        dialog.setDefaultSuffix("pdf")
        return dialog

    def select_file(self) -> None:
        dialog = self._dialog(False)
        if dialog.exec():
            self.inspect_file(dialog.selectedFiles()[0])

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is not None:
            if self.worker.order is not None:
                return
            self.worker.cancelled.set()
        self.preview.reset()
        self.info = None
        self.pages.clear()
        self.modified.clear()
        self.loaded, self.failed = 0, False
        self.details.setText("Verificando o PDF…")
        self.status.setText("Carregando miniaturas localmente…")
        self.progress.setValue(0)
        self._launch(ReorderWorker(self.service, path))

    def _launch(self, worker: ReorderWorker) -> None:
        self._generation += 1
        worker.signals.generation = self._generation
        self.worker = worker
        self.pending_workers.add(worker)
        self.select_button.setEnabled(worker.order is None)
        self.drop_area.setEnabled(worker.order is None)
        self.save_button.setEnabled(False)
        worker.signals.inspected.connect(self.inspected)
        worker.signals.thumbnail.connect(self.thumbnail)
        worker.signals.progress.connect(self.on_progress)
        worker.signals.failed.connect(self.show_error)
        worker.signals.succeeded.connect(self.saved)
        worker.signals.finished.connect(self.finished)
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def inspected(self, info: PdfInfo) -> None:
        if not self.current_session() or self.preview.closing:
            return
        self.info = info
        self.details.setText(f"{info.name} — {info.page_count} páginas — {info.size_bytes:,} bytes".replace(",", "."))
        self.preview.load(info.path, info.page_count or 0, external=True)

    @Slot(int, bytes)
    def thumbnail(self, index: int, data: bytes) -> None:
        if not self.current_session() or self.preview.closing or not self.pages.count():
            return
        self.pages.thumbnail(index, data)
        self.loaded += 1
        total = self.pages.count()
        self.on_progress(int(100 * self.loaded / total), f"{self.loaded} / {total} páginas carregadas")

    @Slot(int, str)
    def on_progress(self, percent: int, message: str) -> None:
        if not self.current_session():
            return
        self.progress.setValue(percent)
        self.status.setText(message)

    @Slot(str)
    def show_error(self, message: str) -> None:
        if not self.current_session():
            return
        self.failed = True
        self.status.setText(message)

    @Slot(str)
    def saved(self, output: str) -> None:
        if not self.current_session():
            return
        self.status.setText(f"PDF reorganizado salvo em:\n{output}")
        self.modified.clear()

    @Slot()
    def finished(self) -> None:
        sender = self.sender()
        completed = next((worker for worker in self.pending_workers if worker.signals is sender), None)
        if completed is not None:
            self.pending_workers.discard(completed)
        if not self.current_session():
            return
        was_saving = self.worker is not None and self.worker.order is not None
        self.worker = None
        if not was_saving:
            self.preview.complete()
        self.select_button.setEnabled(True)
        self.drop_area.setEnabled(True)
        self.pages.setEnabled(True)
        for button in (self.left_button, self.right_button, self.start_button, self.end_button, self.restore_button):
            button.setEnabled(True)
        self.save_button.setEnabled(self.info is not None and (was_saving or not self.failed))

    def current_session(self) -> bool:
        sender = self.sender()
        return sender is None or getattr(sender, "generation", self._generation) == self._generation

    def restore_order(self) -> None:
        if self.pages.order() != tuple(range(self.pages.count())):
            answer = QMessageBox.question(self, "Restaurar ordem", "Descartar as movimentações e restaurar a ordem original?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.pages.restore()

    def update_modified(self) -> None:
        changed = self.pages.order() != tuple(range(self.pages.count()))
        self.modified.setText("Documento modificado — alterações ainda não salvas." if changed else "")

    def choose_output(self) -> None:
        if self.info is None:
            return
        dialog = self._dialog(True)
        path = Path(self.info.path)
        dialog.selectFile(str(path.with_name(path.stem[:100] + "_reorganizado.pdf")))
        if dialog.exec():
            self.save_to(dialog.selectedFiles()[0])

    def save_to(self, output: str) -> None:
        if self.worker is not None or self.info is None:
            return
        self.failed = False
        self.pages.setEnabled(False)
        for button in (self.left_button, self.right_button, self.start_button, self.end_button, self.restore_button):
            button.setEnabled(False)
        self._launch(ReorderWorker(self.service, str(self.info.path), self.pages.order(), output))

    def prepare_close(self) -> None:
        for worker in self.pending_workers:
            if worker.order is None:
                worker.cancelled.set()
