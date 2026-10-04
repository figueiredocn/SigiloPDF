from PySide6.QtCore import Slot

from app.services.remove_pdf_service import RemovePdfError, RemovePdfService
from app.ui.pages.extract_pdf_page import ExtractPdfPage


class RemovePdfPage(ExtractPdfPage):
    service: RemovePdfService
    service_type = RemovePdfService
    page_title = "Remover páginas"
    selection_caption = "Páginas a remover"
    summary_caption = "Resumo antes de processar — páginas removidas e mantidas"
    suggested_suffix = "_sem_paginas.pdf"
    initial_message = "Selecione um PDF e informe as páginas a remover."
    start_message = "Iniciando a remoção local…"

    def update_summary(self, *_args: object) -> None:
        self.summary_valid = False
        if self.info is None:
            self.summary.setPlainText("Selecione um PDF para visualizar o resumo.")
        else:
            try:
                summary = self.service.removal_summary(self.expression.text(), self.info.page_count or 0)
                removed = ", ".join(str(page) for page in summary.removed)
                remaining = ", ".join(str(page) for page in summary.remaining)
                self.summary.setPlainText(f"Remover {len(summary.removed)} página(s): {removed}\nManter {len(summary.remaining)} página(s): {remaining}\nDestino sugerido: {self.output.text()}\nSe existir, será usado um nome com sufixo numérico.")
                self.summary_valid = True
            except RemovePdfError as error:
                self.summary.setPlainText(str(error))
        self.update_controls()

    @Slot(str)
    def show_success(self, path: str) -> None:
        self.status.setText(f"Remoção concluída. Arquivo gerado: {path}")
