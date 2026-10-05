import os
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QFileDialog, QPushButton
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from pypdf import PdfWriter

from app.main import create_application
from app.ui.main_window import MainWindow
from app.ui.components.pdf_drop_area import PdfDropArea


def test_window_and_async_read(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    application.processEvents()
    assert window.isVisible()
    cards = window.stack.widget(0).findChildren(QPushButton)
    assert len(cards) == 13
    assert sum(card.isEnabled() for card in cards) == 13
    next(card for card in cards if card.text() == "Informações do PDF").click()
    assert window.stack.currentIndex() == 1
    path = tmp_path / "teste.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(path)
    window.info_page.inspect_file(str(path))
    assert not window.info_page.select_button.isEnabled()
    deadline = time.monotonic() + 10
    while window.info_page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert window.info_page.worker is None
    assert window.info_page.table.rowCount() == 13
    assert window.info_page.table.item(0, 1).text() == "teste.pdf"
    assert window.info_page.select_button.isEnabled()
    window.close()


def test_drop_accepts_only_one_local_pdf(tmp_path: Path) -> None:
    application = create_application()
    area = PdfDropArea()
    accepted: list[str] = []
    rejected: list[str] = []
    area.file_dropped.connect(accepted.append)
    area.invalid_drop.connect(rejected.append)
    cases = [
        [QUrl.fromLocalFile(str(tmp_path / "documento.pdf"))],
        [QUrl("https://example.invalid/documento.pdf")],
        [QUrl.fromLocalFile(str(tmp_path / "imagem.png"))],
        [QUrl.fromLocalFile(str(tmp_path / "a.pdf")), QUrl.fromLocalFile(str(tmp_path / "b.pdf"))],
    ]
    for urls in cases:
        mime = QMimeData()
        mime.setUrls(urls)
        event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        area.dropEvent(event)
    assert [Path(value) for value in accepted] == [tmp_path / "documento.pdf"]
    assert len(rejected) == 3
    area.close()
    application.processEvents()


def test_ui_recovers_after_read_error(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.info_page
    page.inspect_file(str(tmp_path / "ausente.pdf"))
    deadline = time.monotonic() + 10
    while page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert page.worker is None
    assert page.select_button.isEnabled()
    assert "não foi encontrado" in page.status.text()
    assert page.table.rowCount() == 0
    window.close()


def test_invalid_drop_does_not_interrupt_worker(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.info_page
    page.inspect_file(str(tmp_path / "ausente.pdf"))
    worker = page.worker
    page.drop_area.invalid_drop.emit("Arquivo inválido")
    assert page.worker is worker
    assert not page.select_button.isEnabled()
    deadline = time.monotonic() + 10
    while page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert page.worker is None
    window.close()


def test_qt_translation_is_retained() -> None:
    import gc

    application = create_application()
    gc.collect()
    assert application.translate("QPlatformTheme", "Cancel") == "Cancelar"
    assert create_application() is application


def test_file_dialog_labels_are_portuguese() -> None:
    application = create_application()
    window = MainWindow()
    dialog = window.info_page.create_file_dialog()
    assert dialog.testOption(QFileDialog.Option.DontUseNativeDialog)
    assert dialog.labelText(QFileDialog.DialogLabel.LookIn) == "Examinar:"
    assert dialog.labelText(QFileDialog.DialogLabel.FileType) == "Tipo de arquivo:"
    assert dialog.labelText(QFileDialog.DialogLabel.Reject) == "Cancelar"
    dialog.close()
    window.close()
    application.processEvents()
