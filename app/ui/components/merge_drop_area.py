from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel


class MergeDropArea(QLabel):
    files_dropped = Signal(list)
    invalid_drop = Signal(str)

    def __init__(self) -> None:
        super().__init__("Arraste os PDFs locais para esta área")
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self.setMinimumHeight(75)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self.isEnabled() and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self.isEnabled():
            event.ignore()
            return
        urls = event.mimeData().urls()
        if not urls or any(not url.isLocalFile() or Path(url.toLocalFile()).suffix.lower() != ".pdf" for url in urls):
            self.invalid_drop.emit("Arraste apenas arquivos PDF locais.")
            return
        event.acceptProposedAction()
        self.files_dropped.emit([url.toLocalFile() for url in urls])
