from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel


class PdfDropArea(QLabel):
    file_dropped = Signal(str)
    invalid_drop = Signal(str)

    def __init__(self) -> None:
        super().__init__("Arraste um PDF local para esta área")
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self.setMinimumHeight(90)
        self.setWordWrap(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self.isEnabled() and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self.isEnabled():
            event.ignore()
            return
        urls = event.mimeData().urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            self.invalid_drop.emit("Arraste apenas um arquivo PDF local por vez.")
            return
        path = urls[0].toLocalFile()
        if Path(path).suffix.lower() != ".pdf":
            self.invalid_drop.emit("Selecione um arquivo com extensão .pdf.")
            return
        event.acceptProposedAction()
        self.file_dropped.emit(path)
