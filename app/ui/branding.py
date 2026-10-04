"""Identidade local compartilhada por janelas, diálogos e barra de tarefas."""

from importlib.resources import files
import os

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

WINDOWS_APP_ID = "SigiloPDF.Desktop"


def brand_icon(name: str = "sigilopdf.ico") -> QIcon:
    return QIcon(str(files("app.ui.brand_assets").joinpath(name)))


def configure_windows_identity() -> None:
    """Identifica o processo no Shell do Windows, sem registro ou rede."""
    if os.name != "nt":
        return
    import ctypes
    try:
        setter = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        setter.argtypes = [ctypes.c_wchar_p]
        setter.restype = ctypes.c_long
        setter(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        # Outros sistemas ou shells incompletos continuam usando os ícones do Qt.
        pass


class BrandHeader(QWidget):
    secret_requested = Signal()

    def __init__(self, title: str = "SigiloPDF", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._clicks = 0
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        symbol = QLabel()
        symbol.setAccessibleName("Logotipo do SigiloPDF")
        pixmap = brand_icon("simbolo-claro.svg").pixmap(QSize(96, 96))
        pixmap.setDevicePixelRatio(2)
        symbol.setPixmap(pixmap)
        symbol.setFixedSize(48, 48)
        layout.addWidget(symbol)
        label = QLabel(title)
        label.setObjectName("title")
        layout.addWidget(label)
        layout.addStretch()
        for widget in (symbol, label):
            widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick) and event.button() == Qt.MouseButton.LeftButton:
            self._clicks += 1
            if self._clicks == 5:
                self._clicks = 0
                self.secret_requested.emit()
            return True
        return super().eventFilter(watched, event)
