from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QPushButton, QWidget

from app.services.metadata_service import ANONYMITY_WARNING, EDITABLE_FIELDS, MetadataService, MetadataSnapshot
from app.ui.pages.extract_pdf_page import ExtractPdfPage


class MetadataPage(ExtractPdfPage):
    service_type = MetadataService
    page_title = "Metadados do PDF"
    suggested_suffix = "_metadados_editados.pdf"
    initial_message = "Selecione um PDF para consultar e editar os metadados."
    start_message = "Processando os metadados localmente…"

    def __init__(self) -> None:
        super().__init__()
        self.layout().itemAt(4).widget().hide()
        self.expression.hide()
        self.extract_button.setText("Salvar alterações")
        panel = QWidget()
        form = QFormLayout(panel)
        form.addRow(QLabel("Informações do documento"))
        self.fields = {label: QLineEdit() for label in EDITABLE_FIELDS}
        for label, field in self.fields.items():
            form.addRow(label + ":", field)
        self.technical = QLabel("Informações técnicas indisponíveis.")
        self.technical.setTextFormat(self.details.textFormat())
        self.technical.setWordWrap(True)
        form.addRow(QLabel("Informações técnicas"))
        form.addRow(self.technical)
        self.layout().insertWidget(4, panel)
        self.remove_button = QPushButton("Remover metadados pessoais")
        self.remove_button.clicked.connect(self.remove_metadata)
        self.layout().addWidget(self.remove_button)
        warning = QLabel(ANONYMITY_WARNING)
        warning.setWordWrap(True)
        self.layout().addWidget(warning)
        self.update_controls()

    @Slot(object)
    def show_input(self, snapshot: MetadataSnapshot) -> None:
        info = snapshot.info
        for label, field in self.fields.items():
            field.setText(snapshot.fields[label])
        pages = info.page_count if info.page_count is not None else "Indisponíveis"
        self.technical.setText(f"Criador: {info.creator}\nProdutor: {info.producer}\nData de criação: {info.creation_date}\nData de modificação: {info.modification_date}\nVersão PDF: {info.version}\nPáginas: {pages}\nCriptografia: {'Sim' if info.encrypted else 'Não'}")
        super().show_input(info)
        self.details.setText(f"{info.name} — Páginas: {pages} — {info.size_bytes} bytes")

    @Slot(str)
    def inspect_file(self, path: str) -> None:
        if self.worker is None:
            for field in self.fields.values():
                field.clear()
            self.technical.setText("Verificando as informações técnicas…")
            super().inspect_file(path)

    def update_summary(self, *_args: object) -> None:
        self.summary_valid = self.info is not None and not self.info.encrypted
        self.summary.setPlainText(f"Os metadados serão salvos em uma nova cópia.\nDestino: {self.output.text()}" if self.info else "Selecione um PDF para editar os metadados.")
        if self.info is not None and self.info.encrypted:
            self.summary.setPlainText("Este PDF está protegido por senha. Apenas informações técnicas disponíveis são exibidas.")
        self.update_controls()

    def update_controls(self) -> None:
        super().update_controls()
        if hasattr(self, "fields"):
            for field in self.fields.values():
                field.setEnabled(self.worker is None and self.summary_valid)
            self.remove_button.setEnabled(self.worker is None and self.summary_valid)

    @Slot()
    def start_extract(self) -> None:
        if self.worker is None and self.info is not None and self.summary_valid:
            self.service = MetadataService({label: field.text() for label, field in self.fields.items()})
            super().start_extract()

    def remove_metadata(self) -> None:
        if self.worker is None and self.info is not None and self.summary_valid:
            path = Path(self.info.path)
            destination = Path(self.output.text())
            if destination.name == path.stem[:100] + self.suggested_suffix:
                self.output.setText(str(destination.with_name(path.stem[:100] + "_sem_metadados.pdf")))
            self.service = MetadataService(clear=True)
            super().start_extract()

    @Slot(str)
    def show_success(self, path: str) -> None:
        self.status.setText(f"Metadados processados. Arquivo gerado: {path}")
