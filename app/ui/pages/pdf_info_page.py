from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QAbstractItemView

from app.services.pdf_info_service import PdfInfo, PdfInfoService
from app.ui.components.pdf_drop_area import PdfDropArea
from app.workers.pdf_info_worker import PdfInfoWorker


class PdfInfoPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.service = PdfInfoService()
        self.pool = QThreadPool.globalInstance()
        self.worker: PdfInfoWorker | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Informações do PDF"))
        self.select_button = QPushButton("Selecionar PDF")
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)
        self.drop_area = PdfDropArea()
        self.drop_area.file_dropped.connect(self.inspect_file)
        self.drop_area.invalid_drop.connect(self.show_invalid_input)
        layout.addWidget(self.drop_area)
        self.status = QLabel("Selecione um PDF para consultar suas informações.")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Informação", "Valor"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

    @Slot()
    def select_file(self) -> None:
        dialog = self.create_file_dialog()
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            self.inspect_file(dialog.selectedFiles()[0])

    def create_file_dialog(self) -> QFileDialog:
        dialog = QFileDialog(self, "Selecionar PDF")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setNameFilter("Arquivos PDF (*.pdf *.PDF)")
        labels = {
            QFileDialog.DialogLabel.LookIn: "Examinar:",
            QFileDialog.DialogLabel.FileName: "Nome do arquivo:",
            QFileDialog.DialogLabel.FileType: "Tipo de arquivo:",
            QFileDialog.DialogLabel.Accept: "Abrir",
            QFileDialog.DialogLabel.Reject: "Cancelar",
        }
        for label, text in labels.items():
            dialog.setLabelText(label, text)
        return dialog

    def set_busy(self, busy: bool) -> None:
        self.select_button.setEnabled(not busy)
        self.drop_area.setEnabled(not busy)

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is not None:
            return
        self.table.setRowCount(0)
        self.status.setText("Analisando o PDF localmente…")
        self.set_busy(True)
        self.worker = PdfInfoWorker(self.service, path)
        self.worker.signals.succeeded.connect(self.show_result)
        self.worker.signals.failed.connect(self.show_error)
        self.pool.start(self.worker)

    @Slot(str)
    def show_invalid_input(self, message: str) -> None:
        if self.worker is None:
            self.table.setRowCount(0)
            self.status.setText(message)

    @Slot(str)
    def show_error(self, message: str) -> None:
        self.status.setText(message)
        self.set_busy(False)
        self.worker = None

    @Slot(object)
    def show_result(self, info: PdfInfo) -> None:
        rows = [
            ("Nome do arquivo", info.name), ("Caminho", info.path),
            ("Tamanho", f"{info.size_bytes:,}".replace(",", ".") + " bytes"),
            ("Número de páginas", str(info.page_count) if info.page_count is not None else "Indisponível: PDF protegido"),
            ("Versão PDF", info.version), ("Título", info.title),
            ("Autor", info.author), ("Assunto", info.subject),
            ("Produtor", info.producer), ("Criador", info.creator),
            ("Data de criação (original)", info.creation_date),
            ("Data de modificação (original)", info.modification_date),
            ("Possui criptografia", "Sim" if info.encrypted else "Não"),
        ]
        self.table.setRowCount(len(rows))
        for index, (label, value) in enumerate(rows):
            if info.locked and 4 < index < 12:
                value = "Indisponível: PDF protegido"
            self.table.setItem(index, 0, QTableWidgetItem(label))
            self.table.setItem(index, 1, QTableWidgetItem(value))
        self.table.resizeRowsToContents()
        self.status.setText("PDF protegido por senha: páginas e metadados estão indisponíveis." if info.locked else "Análise concluída. O arquivo foi somente lido.")
        self.set_busy(False)
        self.worker = None
