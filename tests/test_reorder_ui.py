import time
from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from pypdf import PdfReader

from app.main import create_application
from app.ui.main_window import MainWindow
from tests.test_remove_pdf import make_pdf


def wait_worker(page, application) -> None:
    deadline = time.monotonic() + 30
    while page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert page.worker is None


def test_organizer_flow(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    window.stack.setCurrentIndex(7)
    page = window.reorder_page
    source = tmp_path / "relatorio.pdf"
    make_pdf(source, 5)
    before = source.read_bytes()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.drop_area.dropEvent(event)
    wait_worker(page, application)
    assert page.loaded == 5
    assert all(not page.pages.item(row).icon().isNull() for row in range(5))
    page.pages.item(4).setSelected(True)
    class InternalDrop(QDropEvent):
        def source(self):
            return page.pages
    application.processEvents()
    target = page.pages.visualItemRect(page.pages.item(0)).center()
    drag_event = InternalDrop(QPointF(target), Qt.DropAction.MoveAction, QMimeData(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.pages.dropEvent(drag_event)
    assert drag_event.isAccepted()
    assert page.pages.order() == (4, 0, 1, 2, 3)
    assert "alterações ainda não salvas" in page.modified.text()
    page.restore_button.click()
    assert page.pages.order() == (0, 1, 2, 3, 4)
    assert not page.modified.text()
    page.pages.clearSelection()
    page.pages.item(1).setSelected(True)
    page.pages.item(3).setSelected(True)
    page.end_button.click()
    assert page.pages.order() == (0, 2, 4, 1, 3)
    output = tmp_path / "relatorio_reorganizado.pdf"
    page.save_to(str(output))
    wait_worker(page, application)
    reader = PdfReader(output)
    assert [int(p.mediabox.width) for p in reader.pages] == [101, 103, 105, 102, 104]
    assert source.read_bytes() == before
    assert str(output.resolve()) in page.status.text()
    assert not page.modified.text()
    page.inspect_file(str(output))
    wait_worker(page, application)
    assert page.pages.order() == tuple(range(5))
    assert page.loaded == 5
    window.close()


def test_output_error_is_recoverable(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    source = tmp_path / "documento.pdf"
    make_pdf(source, 1)
    page = window.reorder_page
    page.inspect_file(str(source))
    wait_worker(page, application)
    page.save_to(str(source))
    wait_worker(page, application)
    assert "original" in page.status.text()
    # Permitir corrigir o destino sem precisar recarregar o documento.
    assert page.save_button.isEnabled()
    window.close()


def test_large_document_is_progressive(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    source = tmp_path / "grande.pdf"
    make_pdf(source, 500)
    page = window.reorder_page
    page.inspect_file(str(source))
    updates = []
    page.worker.signals.thumbnail.connect(lambda index, data: updates.append(index))
    wait_worker(page, application)
    assert len(updates) == 500
    assert page.loaded == 500
    assert page.progress.value() == 100
    window.close()


def test_close_cancels_thumbnail_loading(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    source = tmp_path / "documento.pdf"
    make_pdf(source, 100)
    page = window.reorder_page
    page.inspect_file(str(source))
    window.close()
    wait_worker(page, application)
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert not window.isVisible()
