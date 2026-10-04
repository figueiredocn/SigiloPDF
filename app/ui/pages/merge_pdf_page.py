from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.services.merge_pdf_service import MergeInput, MergePdfService
from app.ui.components.merge_drop_area import MergeDropArea
from app.workers.merge_pdf_worker import InspectMergeWorker, MergePdfWorker


class MergePdfPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = MergePdfService()
        self.worker: InspectMergeWorker | MergePdfWorker | None = None
        self.errors: list[str] = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Juntar PDFs"))
        self.add_button = QPushButton("Adicionar PDFs")
        self.add_button.clicked.connect(self.select_files)
        layout.addWidget(self.add_button)
        self.drop_area = MergeDropArea()
        self.drop_area.files_dropped.connect(self.add_files)
        self.drop_area.invalid_drop.connect(self.show_invalid_drop)
        layout.addWidget(self.drop_area)
        self.files = QListWidget()
        self.files.currentRowChanged.connect(self.update_controls)
        layout.addWidget(self.files)
        actions = QHBoxLayout()
        self.up_button = QPushButton("Mover para cima")
        self.down_button = QPushButton("Mover para baixo")
        self.remove_button = QPushButton("Remover arquivo")
        self.clear_button = QPushButton("Limpar lista")
        self.up_button.clicked.connect(lambda: self.move_file(-1))
        self.down_button.clicked.connect(lambda: self.move_file(1))
        self.remove_button.clicked.connect(self.remove_file)
        self.clear_button.clicked.connect(self.clear_files)
        for button in (self.up_button, self.down_button, self.remove_button, self.clear_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        output_layout = QHBoxLayout()
        self.output = QLineEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Escolha um novo arquivo de saída")
        self.output.textChanged.connect(self.update_controls)
        self.output_button = QPushButton("Escolher saída")
        self.output_button.clicked.connect(self.select_output)
        output_layout.addWidget(self.output)
        output_layout.addWidget(self.output_button)
        layout.addLayout(output_layout)
        layout.addWidget(QLabel("Os originais são preservados. Arquivos existentes não serão substituídos."))
        self.merge_button = QPushButton("Juntar PDFs")
        self.merge_button.clicked.connect(self.start_merge)
        layout.addWidget(self.merge_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status = QLabel("Adicione pelo menos dois PDFs e organize a ordem da lista.")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.update_controls()

    def file_dialog(self, save: bool) -> QFileDialog:
        dialog = QFileDialog(self, "Escolher arquivo de saída" if save else "Adicionar PDFs")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setNameFilter("Arquivos PDF (*.pdf *.PDF)")
        dialog.setFileMode(QFileDialog.FileMode.AnyFile if save else QFileDialog.FileMode.ExistingFiles)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if save else QFileDialog.AcceptMode.AcceptOpen)
        if save:
            dialog.setDefaultSuffix("pdf")
            dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)
        labels = {
            QFileDialog.DialogLabel.LookIn: "Examinar:",
            QFileDialog.DialogLabel.FileName: "Nome do arquivo:",
            QFileDialog.DialogLabel.FileType: "Tipo de arquivo:",
            QFileDialog.DialogLabel.Accept: "Escolher" if save else "Adicionar",
            QFileDialog.DialogLabel.Reject: "Cancelar",
        }
        for label, text in labels.items():
            dialog.setLabelText(label, text)
        return dialog

    @Slot()
    def select_files(self) -> None:
        dialog = self.file_dialog(False)
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            self.add_files(dialog.selectedFiles())

    @Slot()
    def select_output(self) -> None:
        dialog = self.file_dialog(True)
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            self.output.setText(dialog.selectedFiles()[0])

    @Slot(list)
    def add_files(self, paths: list[str]) -> None:
        if self.worker is not None or not paths:
            return
        self.errors.clear()
        self.progress.setValue(0)
        self.worker = InspectMergeWorker(self.service, list(paths))
        self.worker.signals.inspected.connect(self.append_file)
        self.connect_worker()
        self.status.setText("Verificando os PDFs localmente…")
        QThreadPool.globalInstance().start(self.worker)

    @Slot(object)
    def append_file(self, info: MergeInput) -> None:
        item = QListWidgetItem(f"{info.name} — {info.page_count} página(s)")
        item.setData(Qt.ItemDataRole.UserRole, info)
        item.setToolTip(info.path)
        self.files.addItem(item)
        self.files.setCurrentRow(self.files.count() - 1)

    def connect_worker(self) -> None:
        if self.worker is None:
            return
        self.worker.signals.progress.connect(self.show_progress)
        self.worker.signals.failed.connect(self.show_error)
        self.worker.signals.finished.connect(self.finish_work)
        self.update_controls()

    @Slot()
    def start_merge(self) -> None:
        if self.worker is not None or self.files.count() < 2 or not self.output.text():
            return
        paths = [self.files.item(index).data(Qt.ItemDataRole.UserRole).path for index in range(self.files.count())]
        self.errors.clear()
        self.progress.setValue(0)
        self.worker = MergePdfWorker(self.service, paths, self.output.text())
        self.worker.signals.succeeded.connect(self.show_success)
        self.connect_worker()
        self.status.setText("Iniciando a junção local…")
        QThreadPool.globalInstance().start(self.worker)

    @Slot(int, str)
    def show_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        if not self.errors:
            self.status.setText(message)

    @Slot(str)
    def show_success(self, path: str) -> None:
        self.status.setText(f"PDF gerado com sucesso: {path}")

    @Slot(str)
    def show_error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)
        self.status.setText("\n".join(self.errors))

    @Slot(str)
    def show_invalid_drop(self, message: str) -> None:
        if self.worker is None:
            self.status.setText(message)

    @Slot()
    def finish_work(self) -> None:
        if isinstance(self.worker, InspectMergeWorker) and not self.errors:
            self.status.setText("Arquivos adicionados. Organize a ordem e escolha a saída.")
        self.worker = None
        self.update_controls()

    def update_controls(self, *_args: object) -> None:
        idle = self.worker is None
        row, count = self.files.currentRow(), self.files.count()
        for widget in (self.add_button, self.drop_area, self.files, self.output_button):
            widget.setEnabled(idle)
        self.up_button.setEnabled(idle and row > 0)
        self.down_button.setEnabled(idle and 0 <= row < count - 1)
        self.remove_button.setEnabled(idle and row >= 0)
        self.clear_button.setEnabled(idle and count > 0)
        self.merge_button.setEnabled(idle and count >= 2 and bool(self.output.text()))

    def move_file(self, offset: int) -> None:
        row = self.files.currentRow()
        destination = row + offset
        if self.worker is None and 0 <= row < self.files.count() and 0 <= destination < self.files.count():
            item = self.files.takeItem(row)
            self.files.insertItem(destination, item)
            self.files.setCurrentRow(destination)
            self.update_controls()

    @Slot()
    def remove_file(self) -> None:
        if self.worker is None:
            self.files.takeItem(self.files.currentRow())
            self.update_controls()

    @Slot()
    def clear_files(self) -> None:
        if self.worker is None:
            self.files.clear()
            self.progress.setValue(0)
            self.status.setText("Lista limpa. Adicione pelo menos dois PDFs.")
            self.update_controls()
