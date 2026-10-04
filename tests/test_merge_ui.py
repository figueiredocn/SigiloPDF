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


def wait_for_page(window: MainWindow) -> None:
    application = create_application()
    deadline = time.monotonic() + 10
    while window.merge_page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert window.merge_page.worker is None


def source_pdf(path: Path, width: int) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=300)
    writer.write(path)


def test_merge_workflow_with_drop_order_and_output(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    card = next(button for button in window.stack.widget(0).findChildren(QPushButton) if button.text() == "Juntar PDFs")
    card.click()
    assert window.stack.currentIndex() == 2
    page = window.merge_page
    paths = [tmp_path / "um.pdf", tmp_path / "dois.pdf"]
    for index, path in enumerate(paths):
        source_pdf(path, 100 + index)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    drop = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.drop_area.dropEvent(drop)
    assert page.worker is not None
    assert not page.add_button.isEnabled()
    wait_for_page(window)
    assert page.files.count() == 2
    assert "um.pdf" in page.files.item(0).text()
    assert "1 página(s)" in page.files.item(0).text()
    page.files.setCurrentRow(1)
    page.up_button.click()
    assert "dois.pdf" in page.files.item(0).text()
    page.down_button.click()
    assert "dois.pdf" in page.files.item(1).text()
    page.up_button.click()
    output = tmp_path / "juntos.pdf"
    page.output.setText(str(output))
    page.merge_button.click()
    assert not page.clear_button.isEnabled()
    wait_for_page(window)
    assert page.progress.value() == 100
    assert "sucesso" in page.status.text()
    with output.open("rb") as stream:
        assert [float(p.mediabox.width) for p in PdfReader(stream).pages] == [101, 100]
    page.files.setCurrentRow(0)
    page.remove_button.click()
    assert page.files.count() == 1
    assert not page.merge_button.isEnabled()
    page.clear_button.click()
    assert page.files.count() == 0
    assert not page.clear_button.isEnabled()
    window.close()
    application.processEvents()


def test_rejected_input_and_existing_output_recover(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.merge_page
    first, second = tmp_path / "um.pdf", tmp_path / "dois.pdf"
    source_pdf(first, 100)
    source_pdf(second, 200)
    page.add_files([str(first), str(tmp_path / "ausente.pdf"), str(second)])
    wait_for_page(window)
    assert page.files.count() == 2
    assert "não foi encontrado" in page.status.text()
    output = tmp_path / "existente.pdf"
    output.write_bytes(b"preservar")
    page.output.setText(str(output))
    page.start_merge()
    wait_for_page(window)
    assert "já existe" in page.status.text()
    assert output.read_bytes() == b"preservar"
    assert page.add_button.isEnabled()
    page.output.setText(str(tmp_path / "novo.pdf"))
    page.start_merge()
    wait_for_page(window)
    assert "sucesso" in page.status.text()
    window.close()
    application.processEvents()
