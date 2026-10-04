from PySide6.QtCore import Slot
from PySide6.QtWidgets import QComboBox, QFormLayout, QSpinBox, QWidget

from app.services.number_pdf_service import FONT_SIZES, FORMATS, POSITIONS, NumberPdfService, NumberSettings, PdfEditError, number_label
from app.ui.pages.extract_pdf_page import ExtractPdfPage


class NumberPdfPage(ExtractPdfPage):
    service_type = NumberPdfService
    page_title = "Numerar páginas"
    selection_caption = "Intervalo ou páginas específicas"
    summary_caption = "Resumo da numeração"
    suggested_suffix = "_numerado.pdf"
    initial_message = "Selecione um PDF para inserir numeração visual."
    start_message = "Iniciando a numeração local…"

    def __init__(self) -> None:
        super().__init__()
        panel = QWidget()
        form = QFormLayout(panel)
        self.scope = QComboBox()
        self.scope.addItems(("Todas as páginas", "Intervalo", "Páginas específicas / combinação"))
        self.first_number = QSpinBox()
        self.first_number.setRange(0, 1_000_000)
        self.first_number.setValue(1)
        self.start_page = QSpinBox()
        self.start_page.setRange(1, 1_000_000)
        self.format = QComboBox()
        self.format.addItems(FORMATS)
        self.position = QComboBox()
        self.position.addItems(POSITIONS)
        self.position.setCurrentText("Inferior central")
        self.font_size = QComboBox()
        self.font_size.addItems(tuple(FONT_SIZES))
        self.font_size.setCurrentText("Médio")
        for text, widget in (("Páginas:", self.scope), ("Número inicial:", self.first_number), ("Página inicial da numeração:", self.start_page),
                             ("Formato:", self.format), ("Posição:", self.position), ("Tamanho:", self.font_size)):
            form.addRow(text, widget)
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.update_summary)
            else:
                widget.valueChanged.connect(self.update_summary)
        self.layout().insertWidget(4, panel)
        self.update_summary()

    def settings(self) -> NumberSettings:
        return NumberSettings(None if self.scope.currentIndex() == 0 else self.expression.text(), self.first_number.value(),
                              self.start_page.value(), self.format.currentText(), self.position.currentText(), self.font_size.currentText())

    def update_summary(self, *_args: object) -> None:
        self.summary_valid = False
        if not hasattr(self, "scope") or self.info is None:
            self.summary.setPlainText("Selecione um PDF para visualizar o resumo.")
        else:
            try:
                settings = self.settings()
                pages = self.service.summarize_numbering(settings, self.info.page_count or 0)
                label = number_label(settings.first_number, self.info.page_count or 0, settings.format)
                self.summary.setPlainText(f"Páginas numeradas: {', '.join(map(str, pages))}\nPrimeiro rótulo: {label}\nPosição: {settings.position}\nO total do formato corresponde às páginas do documento. Margem: 18 pontos.\nDestino: {self.output.text()}")
                self.summary_valid = True
            except PdfEditError as error:
                self.summary.setPlainText(str(error))
        self.update_controls()

    def update_controls(self) -> None:
        super().update_controls()
        if hasattr(self, "scope"):
            for widget in (self.scope, self.first_number, self.start_page, self.format, self.position, self.font_size):
                widget.setEnabled(self.worker is None)
            self.expression.setEnabled(self.worker is None and self.scope.currentIndex() != 0)

    @Slot(object)
    def show_input(self, info) -> None:
        super().show_input(info)
        self.details.setText(f"{info.name} — {info.page_count} páginas — {info.size_bytes} bytes")

    @Slot()
    def start_extract(self) -> None:
        if self.worker is None and self.info is not None and self.summary_valid:
            self.service = NumberPdfService(self.settings())
            super().start_extract()

    @Slot(str)
    def show_success(self, path: str) -> None:
        self.status.setText(f"Numeração concluída. Arquivo gerado: {path}")
