from importlib.resources import files
from pathlib import Path
import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QLabel
import pytest

from app.main import create_application
from app.ui.branding import BrandHeader, WINDOWS_APP_ID, brand_icon
from app.ui.components.about_dialog import AboutDialog
from app.ui.main_window import MainWindow


@pytest.mark.parametrize("name", ["sigilopdf.ico", "icone-app.svg", "simbolo-claro.svg", "simbolo-escuro.svg", "simbolo-monocromatico.svg"])
def test_brand_assets_are_packaged_and_loadable(tmp_path: Path, monkeypatch, name: str) -> None:
    application = create_application()
    monkeypatch.chdir(tmp_path)
    assert files("app.ui.brand_assets").joinpath(name).is_file()
    icon = brand_icon(name)
    assert not icon.isNull()
    for size in (16, 32, 64, 128, 256):
        assert not icon.pixmap(size, size).isNull()
    application.processEvents()


def test_all_windows_and_dialogs_inherit_application_icon() -> None:
    application = create_application()
    window = MainWindow()
    about = AboutDialog(window)
    dialog = QFileDialog(window)
    assert not application.windowIcon().isNull()
    for widget in (window, about, dialog):
        assert not widget.windowIcon().isNull()
    assert len(window.findChildren(BrandHeader)) == 1
    assert not about.logo.icon().isNull()
    dialog.close()
    about.close()
    window.close()


def test_five_real_logo_clicks_and_interrupted_sequence() -> None:
    application = create_application()
    about = AboutDialog()
    about.show()
    application.processEvents()
    for _ in range(4):
        QTest.mouseClick(about.logo, Qt.MouseButton.LeftButton)
    assert about.special_dialog is None
    description = next(label for label in about.findChildren(QLabel) if label.text().startswith("Toolkit"))
    QTest.mouseClick(description, Qt.MouseButton.LeftButton, pos=QPoint(3, 3))
    for _ in range(4):
        QTest.mouseClick(about.logo, Qt.MouseButton.LeftButton)
    assert about.special_dialog is None
    QTest.mouseClick(about.logo, Qt.MouseButton.LeftButton)
    application.processEvents()
    special = about.special_dialog
    assert special is not None and special.isVisible()
    assert not special.windowIcon().isNull()
    assert len(special.findChildren(BrandHeader)) == 1
    special.close()
    for _ in range(5):
        QTest.mouseClick(about.logo, Qt.MouseButton.LeftButton)
    application.processEvents()
    assert about.special_dialog is not special
    assert about.special_dialog.isVisible()
    about.special_dialog.close()
    about.close()


@pytest.mark.skipif(os.name != "nt", reason="Identidade da barra de tarefas exclusiva do Windows")
def test_windows_taskbar_identity() -> None:
    import ctypes
    create_application()
    pointer = ctypes.c_void_p()
    getter = ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID
    getter.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    getter.restype = ctypes.c_long
    assert getter(ctypes.byref(pointer)) == 0
    try:
        assert ctypes.wstring_at(pointer) == WINDOWS_APP_ID
    finally:
        ctypes.windll.ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.ole32.CoTaskMemFree(pointer)


def test_main_logo_opens_special_message() -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    application.processEvents()
    header = window.findChild(BrandHeader)
    logo = next(label for label in header.findChildren(QLabel) if label.accessibleName() == "Logotipo do SigiloPDF")
    for _ in range(5):
        QTest.mouseClick(logo, Qt.MouseButton.LeftButton)
    application.processEvents()
    about = window.findChild(AboutDialog)
    assert about is not None
    assert about.special_dialog is not None and about.special_dialog.isVisible()
    about.special_dialog.close()
    about.close()
    window.close()


def test_fast_double_clicks_and_keyboard_alternative() -> None:
    application = create_application()
    about = AboutDialog()
    about.show()
    about.activateWindow()
    application.processEvents()
    for _ in range(2):
        QTest.mouseClick(about.logo, Qt.MouseButton.LeftButton)
        QTest.mouseDClick(about.logo, Qt.MouseButton.LeftButton)
    assert about.special_dialog is None
    QTest.mouseClick(about.logo, Qt.MouseButton.LeftButton)
    application.processEvents()
    assert about.special_dialog is not None and about.special_dialog.isVisible()
    about.special_dialog.close()
    about.activateWindow()
    about.logo.setFocus()
    QTest.qWait(50)
    previous = about.special_dialog
    QTest.keyClick(about.logo, Qt.Key.Key_P, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    application.processEvents()
    assert about.special_dialog is not previous
    assert about.special_dialog.isVisible()
    about.special_dialog.close()
    about.close()
