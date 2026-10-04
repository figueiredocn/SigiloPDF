import os
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QPushButton
from pypdf import PdfReader, PdfWriter

from app.main import create_application
from app.services.split_pdf_service import SplitMode
from app.ui.main_window import MainWindow


def wait_for_split(window: MainWindow) -> None:
    application = create_application()
    deadline = time.monotonic() + 10
    while window.split_page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert window.split_page.worker is None


def make_source(path: Path) -> None:
    writer = PdfWriter()
    for width in (101, 102, 103):
        writer.add_blank_page(width=width, height=300)
    writer.write(path)


def test_split_drop_details_and_generation(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    card = next(button for button in window.stack.widget(0).findChildren(QPushButton) if button.text() == "Dividir PDF")
    card.click()
    assert window.stack.currentIndex() == 3
    page = window.split_page
    source = tmp_path / "documento.pdf"
    make_source(source)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.drop_area.dropEvent(event)
    assert page.worker is not None
    assert not page.select_button.isEnabled()
    wait_for_split(window)
    assert page.info is not None
    assert "documento.pdf" in page.file_details.text()
    assert "3 página(s)" in page.file_details.text()
    assert f"{source.stat().st_size:,}".replace(",", ".") in page.file_details.text()
    page.folder.setText(str(tmp_path))
    assert not page.expression.isEnabled()
    page.split_button.click()
    assert not page.folder_button.isEnabled()
    wait_for_split(window)
    assert page.progress.value() == 100
    assert "3 arquivo(s)" in page.status.text()
    assert len(page.results.toPlainText().splitlines()) == 3
    assert (tmp_path / "documento_pagina_001.pdf").is_file()
    window.close()
    application.processEvents()


def test_split_invalid_selection_recovery_and_conflicts(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.split_page
    source = tmp_path / "documento.pdf"
    make_source(source)
    page.inspect_file(str(source))
    wait_for_split(window)
    page.folder.setText(str(tmp_path))
    page.mode.setCurrentIndex(page.mode.findData(SplitMode.COMBINATION))
    page.expression.setText("1,,3")
    page.start_split()
    wait_for_split(window)
    assert "Seleção inválida" in page.status.text()
    assert page.select_button.isEnabled()
    assert page.results.toPlainText() == ""
    page.expression.setText("3,1,1")
    page.start_split()
    wait_for_split(window)
    path = Path(page.results.toPlainText())
    with path.open("rb") as stream:
        assert [int(p.mediabox.width) for p in PdfReader(stream).pages] == [101, 103]
    page.start_split()
    wait_for_split(window)
    assert Path(page.results.toPlainText()).name == "documento_paginas_1,3_2.pdf"
    assert path.exists()
    window.close()
    application.processEvents()


def test_invalid_pdf_clears_previous_input(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.split_page
    source = tmp_path / "documento.pdf"
    make_source(source)
    page.inspect_file(str(source))
    wait_for_split(window)
    page.inspect_file(str(tmp_path / "ausente.pdf"))
    wait_for_split(window)
    assert page.info is None
    assert not page.split_button.isEnabled()
    assert "não foi encontrado" in page.status.text()
    window.close()
    application.processEvents()
