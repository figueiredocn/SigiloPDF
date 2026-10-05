from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QMainWindow, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from app.ui.pages.pdf_info_page import PdfInfoPage
from app.ui.pages.merge_pdf_page import MergePdfPage
from app.ui.pages.split_pdf_page import SplitPdfPage
from app.ui.pages.extract_pdf_page import ExtractPdfPage
from app.ui.pages.remove_pdf_page import RemovePdfPage
from app.ui.pages.rotate_pdf_page import RotatePdfPage
from app.ui.pages.reorder_pdf_page import ReorderPdfPage
from app.ui.pages.images_pdf_page import ImagesPdfPage
from app.ui.pages.pdf_images_page import PdfImagesPage
from app.ui.pages.number_pdf_page import NumberPdfPage
from app.ui.pages.metadata_page import MetadataPage
from app.ui.pages.protection_page import ProtectionPage
from app.ui.pages.compression_page import CompressionPage
from app.ui.components.about_dialog import AboutDialog
from app.ui.components.page_preview_panel import PagePreviewPanel
from app.ui.components.update_controller import UpdateController
from app.ui.branding import BrandHeader, brand_icon


TOOLS = ["Juntar PDFs", "Dividir PDF", "Extrair páginas", "Organizar páginas", "Girar páginas", "Remover páginas", "Imagens para PDF", "PDF para imagens", "Numerar páginas", "Metadados", "Proteger PDF", "Informações do PDF", "Comprimir PDF"]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._close_requested = False
        self._close_timer = QTimer(self)
        self._close_timer.setInterval(100)
        self._close_timer.timeout.connect(self._finish_close)
        self.setWindowTitle("SigiloPDF")
        self.setWindowIcon(brand_icon())
        self.resize(1000, 760)
        container = QWidget()
        layout = QVBoxLayout(container)
        header = BrandHeader()
        header.secret_requested.connect(self.show_special)
        layout.addWidget(header)
        layout.addWidget(QLabel("Seus documentos. Seu computador. Seu controle."))
        layout.addWidget(QLabel("Seus arquivos são processados localmente."))
        self.stack = QStackedWidget()
        home = QWidget()
        grid = QGridLayout(home)
        page_indexes = {"Informações do PDF": 1, "Juntar PDFs": 2, "Dividir PDF": 3, "Extrair páginas": 4, "Remover páginas": 5, "Girar páginas": 6, "Organizar páginas": 7, "Imagens para PDF": 8, "PDF para imagens": 9, "Numerar páginas": 10, "Metadados": 11, "Proteger PDF": 12, "Comprimir PDF": 13}
        for index, name in enumerate(TOOLS):
            available = name in page_indexes
            card = QPushButton(name if available else name + "\nEm breve")
            card.setMinimumHeight(95)
            card.setEnabled(available)
            if name == "Comprimir PDF":
                card.setIcon(brand_icon("comprimir.svg"))
            if available:
                page_index = page_indexes[name]
                card.clicked.connect(lambda checked=False, index=page_index: self.stack.setCurrentIndex(index))
            grid.addWidget(card, index // 3, index % 3)
        self._add_tool_page(home)
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        back = QPushButton("← Voltar às ferramentas")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        detail_layout.addWidget(back)
        self.info_page = PdfInfoPage()
        detail_layout.addWidget(self.info_page)
        self._add_tool_page(detail)
        merge_detail = QWidget()
        merge_layout = QVBoxLayout(merge_detail)
        merge_back = QPushButton("← Voltar às ferramentas")
        merge_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        merge_layout.addWidget(merge_back)
        self.merge_page = MergePdfPage()
        merge_layout.addWidget(self.merge_page)
        self._add_tool_page(merge_detail)
        split_detail = QWidget()
        split_layout = QVBoxLayout(split_detail)
        split_back = QPushButton("← Voltar às ferramentas")
        split_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        split_layout.addWidget(split_back)
        self.split_page = SplitPdfPage()
        split_layout.addWidget(self.split_page)
        self._add_tool_page(split_detail)
        extract_detail = QWidget()
        extract_layout = QVBoxLayout(extract_detail)
        extract_back = QPushButton("← Voltar às ferramentas")
        extract_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        extract_layout.addWidget(extract_back)
        self.extract_page = ExtractPdfPage()
        extract_layout.addWidget(self.extract_page)
        self._add_tool_page(extract_detail)
        remove_detail = QWidget()
        remove_layout = QVBoxLayout(remove_detail)
        remove_back = QPushButton("← Voltar às ferramentas")
        remove_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        remove_layout.addWidget(remove_back)
        self.remove_page = RemovePdfPage()
        remove_layout.addWidget(self.remove_page)
        self._add_tool_page(remove_detail)
        rotate_detail = QWidget()
        rotate_layout = QVBoxLayout(rotate_detail)
        rotate_back = QPushButton("← Voltar às ferramentas")
        rotate_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        rotate_layout.addWidget(rotate_back)
        self.rotate_page = RotatePdfPage()
        rotate_layout.addWidget(self.rotate_page)
        self._add_tool_page(rotate_detail)
        organize_detail = QWidget()
        organize_layout = QVBoxLayout(organize_detail)
        organize_back = QPushButton("Voltar às ferramentas")
        organize_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        organize_layout.addWidget(organize_back)
        self.reorder_page = ReorderPdfPage()
        organize_layout.addWidget(self.reorder_page)
        self._add_tool_page(organize_detail)
        images_detail = QWidget()
        images_layout = QVBoxLayout(images_detail)
        images_back = QPushButton("← Voltar às ferramentas")
        images_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        images_layout.addWidget(images_back)
        self.images_page = ImagesPdfPage()
        images_layout.addWidget(self.images_page)
        self._add_tool_page(images_detail)
        export_detail = QWidget()
        export_layout = QVBoxLayout(export_detail)
        export_back = QPushButton("← Voltar às ferramentas")
        export_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        export_layout.addWidget(export_back)
        self.pdf_images_page = PdfImagesPage()
        export_layout.addWidget(self.pdf_images_page)
        self._add_tool_page(export_detail)
        for attribute, page_type in (("number_page", NumberPdfPage), ("metadata_page", MetadataPage), ("protection_page", ProtectionPage), ("compression_page", CompressionPage)):
            detail = QWidget()
            detail_layout = QVBoxLayout(detail)
            back = QPushButton("← Voltar às ferramentas")
            back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
            detail_layout.addWidget(back)
            page = page_type()
            setattr(self, attribute, page)
            detail_layout.addWidget(page)
            self._add_tool_page(detail)
        layout.addWidget(self.stack)
        help_menu = self.menuBar().addMenu("Ajuda")
        about = help_menu.addAction("Sobre o SigiloPDF")
        about.triggered.connect(self.show_about)
        self.updates = UpdateController(self)
        help_menu.addAction("Verificar atualizações").triggered.connect(self.updates.check_manual)
        self.setCentralWidget(container)

    def show_about(self) -> None:
        dialog = AboutDialog(self)
        dialog.update_requested.connect(self.updates.check_manual)
        dialog.exec()

    def show_special(self) -> None:
        dialog = AboutDialog(self)
        dialog.show()
        dialog.show_special()

    def _add_tool_page(self, page: QWidget) -> None:
        # Campos e mensagens devem continuar acessíveis em telas menores.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        self.stack.addWidget(scroll)

    def _has_pending_work(self) -> bool:
        pages = (self.info_page, self.merge_page, self.split_page, self.extract_page, self.remove_page, self.rotate_page, self.reorder_page, self.images_page, self.pdf_images_page, self.number_page, self.metadata_page, self.protection_page, self.compression_page)
        return (any(page.worker is not None for page in pages)
                or self.updates.pending()
                or bool(self.reorder_page.pending_workers)
                or any(panel.has_pending_work() for panel in self.findChildren(PagePreviewPanel))
                or QThreadPool.globalInstance().activeThreadCount() > 0)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.updates.prepare_close()
        for panel in self.findChildren(PagePreviewPanel):
            panel.prepare_close()
        self.reorder_page.prepare_close()
        self.pdf_images_page.prepare_close()
        self.compression_page.prepare_close()
        if self._has_pending_work():
            event.ignore()
            self._close_requested = True
            self.centralWidget().setEnabled(False)
            self.statusBar().showMessage("Aguarde a conclusão da operação. A janela será fechada em seguida.")
            if not self._close_timer.isActive():
                self._close_timer.start()
            return
        self._close_timer.stop()
        self.protection_page.clear_passwords()
        self.protection_page.service.release_secrets()
        self.reorder_page.pages.clear()
        self.images_page.images.clear()
        self.pdf_images_page.pages.clear()
        self.compression_page.cleanup()
        for panel in self.findChildren(PagePreviewPanel):
            panel.reset()
        super().closeEvent(event)

    def _finish_close(self) -> None:
        if self._close_requested and not self._has_pending_work():
            self.close()
