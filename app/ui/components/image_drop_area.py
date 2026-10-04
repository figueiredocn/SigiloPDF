from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel


class ImageDropArea(QLabel):
    files_dropped = Signal(object)
    invalid_drop = Signal(str)

    def __init__(self) -> None:
        super().__init__("Arraste imagens JPG, JPEG, PNG ou BMP para esta área")
        self.setObjectName("dropArea")
        self.setWordWrap(True)
        self.setMinimumHeight(90)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self.isEnabled() and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self.isEnabled():
            event.ignore()
            return
        urls = event.mimeData().urls()
        if not urls or any(not url.isLocalFile() or Path(url.toLocalFile()).suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp") for url in urls):
            self.invalid_drop.emit("Arraste apenas imagens locais JPG, JPEG, PNG ou BMP.")
            event.ignore()
            return
        event.acceptProposedAction()
        self.files_dropped.emit(tuple(url.toLocalFile() for url in urls))
