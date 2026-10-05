from PySide6.QtCore import Slot
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from app.services.rotate_pdf_service import RotatePdfError, RotatePdfService
from app.ui.pages.extract_pdf_page import ExtractPdfPage


class RotatePdfPage(ExtractPdfPage):
    service: RotatePdfService
    service_type = RotatePdfService
    page_title = "Girar páginas"
    selection_caption = "Páginas selecionadas"
    summary_caption = "Resumo antes de processar — páginas afetadas e direção da rotação"
    suggested_suffix = "_girado.pdf"
    initial_message = "Selecione um PDF e escolha a rotação."
    start_message = "Iniciando a rotação local…"

    def __init__(self) -> None:
        super().__init__()
        self.scope = QComboBox()
        self.scope.addItem("Todas as páginas", True)
        self.scope.addItem("Somente páginas selecionadas", False)
        self.direction = QComboBox()
        self.direction.addItem("90° horário", 90)
        self.direction.addItem("90° anti-horário", -90)
        self.direction.addItem("180°", 180)
        layout = self.layout()
        layout.insertWidget(4, QLabel("Aplicar em"))
        layout.insertWidget(5, self.scope)
        layout.insertWidget(8, QLabel("Direção da rotação"))
        layout.insertWidget(9, self.direction)
        self.scope.currentIndexChanged.connect(self.update_summary)
        self.direction.currentIndexChanged.connect(self.update_summary)
        actions = QHBoxLayout()
        self.quick_buttons = []
        for text, direction in (("↶ Girar à esquerda", -90), ("↷ Girar à direita", 90), ("⟳ 180°", 180)):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, angle=direction: self.quick_rotation(angle))
            self.quick_buttons.append(button)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.update_summary()

    def choose_visual_mode(self) -> None:
        self.scope.setCurrentIndex(1)

    def quick_rotation(self, angle: int) -> None:
        self.direction.setCurrentIndex(self.direction.findData(angle))

    def update_summary(self, *_args: object) -> None:
        self.summary_valid = False
        if not hasattr(self, "scope") or self.info is None:
            self.summary.setPlainText("Selecione um PDF para visualizar o resumo.")
        else:
            try:
                summary = self.service.rotation_summary(self.expression.text(), self.info.page_count or 0, self.direction.currentData(), self.scope.currentData())
                pages = ", ".join(str(page) for page in summary.pages)
                self.summary.setPlainText(f"Páginas afetadas ({len(summary.pages)}): {pages}\nRotação: {self.direction.currentText()}, adicional à orientação atual.\nDestino sugerido: {self.output.text()}\nSe existir, será usado um nome com sufixo numérico.")
                self.summary_valid = True
                if hasattr(self, "preview"):
                    self.preview.pages.set_rotations({page - 1: self.direction.currentData() for page in summary.pages})
            except RotatePdfError as error:
                self.summary.setPlainText(str(error))
                if hasattr(self, "preview"):
                    self.preview.pages.set_rotations({})
        self.update_controls()

    def update_controls(self) -> None:
        super().update_controls()
        if hasattr(self, "scope"):
            idle = self.worker is None
            self.scope.setEnabled(idle)
            self.direction.setEnabled(idle)
            self.expression.setEnabled(idle and not self.scope.currentData())
            if hasattr(self, "preview"):
                if self.scope.currentData():
                    self.preview.pages.select_pages(tuple(range(self.preview.pages.count())))
                else:
                    self.preview.sync_text()
            for button in getattr(self, "quick_buttons", ()):
                button.setEnabled(idle and self.info is not None)

    @Slot()
    def start_extract(self) -> None:
        if self.worker is None and self.info is not None and self.summary_valid:
            # O worker recebe sua própria configuração, fixa durante a operação.
            self.service = RotatePdfService(self.direction.currentData(), self.scope.currentData())
            super().start_extract()

    @Slot(str)
    def show_success(self, path: str) -> None:
        self.status.setText(f"Rotação concluída. Arquivo gerado: {path}")
