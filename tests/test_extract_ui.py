import os
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QPushButton
from pypdf import PdfReader, PdfWriter

from app.main import create_application
from app.ui.main_window import MainWindow


def wait_for_extract(window: MainWindow) -> None:
    application = create_application()
    deadline = time.monotonic() + 10
    while window.extract_page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert window.extract_page.worker is None


def test_extract_drag_summary_and_generation(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    next(card for card in window.stack.widget(0).findChildren(QPushButton) if card.text() == "Extrair páginas").click()
    assert window.stack.currentIndex() == 4
    source = tmp_path / "relatorio.pdf"
    writer = PdfWriter()
    for number in range(1, 9):
        writer.add_blank_page(width=100 + number, height=300)
    writer.write(source)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page = window.extract_page
    page.drop_area.dropEvent(event)
    assert not page.select_button.isEnabled()
    wait_for_extract(window)
    assert "8 página(s)" in page.details.text()
    assert page.output.text() == str(tmp_path / "relatorio_extraido.pdf")
    page.expression.setText("9")
    assert not page.extract_button.isEnabled()
    assert "não existe" in page.summary.toPlainText()
    page.expression.setText("8,2-4,2")
    assert "4 página(s)" in page.summary.toPlainText()
    assert "Ordem de extração: 8, 2, 3, 4" in page.summary.toPlainText()
    assert not (tmp_path / "relatorio_extraido.pdf").exists()
    page.extract_button.click()
    assert not page.expression.isEnabled()
    wait_for_extract(window)
    assert page.progress.value() == 100
    with (tmp_path / "relatorio_extraido.pdf").open("rb") as stream:
        assert [int(p.mediabox.width) - 100 for p in PdfReader(stream).pages] == [8, 2, 3, 4]
    page.extract_button.click()
    wait_for_extract(window)
    assert "relatorio_extraido_2.pdf" in page.status.text()
    window.close()
    application.processEvents()
