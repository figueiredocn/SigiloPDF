from pathlib import Path
import time

from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QLineEdit
import pymupdf
from pypdf import PdfReader

from app.main import create_application
from app.ui.main_window import MainWindow
from tests.test_images_to_pdf import make_image


def wait(page, application) -> None:
    deadline = time.monotonic() + 20
    while page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert page.worker is None


def test_images_flow(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    window.stack.setCurrentIndex(8)
    page = window.images_page
    paths = [make_image(tmp_path / "retrato.jpg", (120, 200), color="red"),
             make_image(tmp_path / "paisagem.bmp", (200, 120), color="blue"),
             make_image(tmp_path / "transparente.png", (100, 100), "RGBA", (0, 0, 0, 0))]
    before = [path.read_bytes() for path in paths]
    def select_in_dialog() -> None:
        dialog = application.activeModalWidget()
        dialog.setDirectory(str(tmp_path.resolve()))
        def accept_selection() -> None:
            dialog.findChild(QLineEdit, "fileNameEdit").setText(" ".join(f'"{path.name}"' for path in paths))
            dialog.accept()
        QTimer.singleShot(300, accept_selection)
    QTimer.singleShot(100, select_in_dialog)
    page.select_images()
    wait(page, application)
    assert page.images.count() == 3
    assert all(not page.images.item(row).icon().isNull() for row in range(3))
    assert page.page_size.currentText() == "A4"
    assert page.margin.currentText() == "Pequena"
    page.images.item(1).setSelected(True)
    page.action_buttons[0].click()
    assert Path(page.images.item(0).data(Qt.ItemDataRole.UserRole)).name == "paisagem.bmp"
    page.action_buttons[1].click()
    page.images.clearSelection()
    page.images.item(2).setSelected(True)
    class InternalDrop(QDropEvent):
        def source(self):
            return page.images
    application.processEvents()
    target = page.images.visualItemRect(page.images.item(0)).center()
    event = InternalDrop(QPointF(target), Qt.DropAction.MoveAction, QMimeData(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.images.dropEvent(event)
    output = tmp_path / "imagens_convertidas.pdf"
    page.generate_to(str(output))
    wait(page, application)
    reader = PdfReader(output)
    assert len(reader.pages) == 3
    assert [page["/Resources"]["/XObject"]["/Imagem"]["/Width"] for page in reader.pages] == [100, 120, 200]
    assert reader.pages[1].mediabox.width < reader.pages[1].mediabox.height
    assert reader.pages[2].mediabox.width > reader.pages[2].mediabox.height
    # Abrir e renderizar a saída: transparência branca, retrato vermelho e paisagem azul.
    with pymupdf.open(output) as document:
        for index, expected in enumerate(((255, 255, 255), (254, 0, 0), (0, 0, 255))):
            pixmap = document[index].get_pixmap(matrix=pymupdf.Matrix(0.2, 0.2), alpha=False)
            actual = pixmap.pixel(pixmap.width // 2, pixmap.height // 2)
            assert all(abs(a - b) <= 2 for a, b in zip(actual, expected))
    assert [path.read_bytes() for path in paths] == before
    assert str(output.resolve()) in page.status.text()
    page.images.item(0).setSelected(True)
    page.remove_images()
    assert page.images.count() == 2
    page.clear_images()
    assert not page.generate_button.isEnabled()
    # Conferir também a entrada de múltiplos arquivos por arraste.
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    page.drop_area.dropEvent(QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    wait(page, application)
    assert page.images.count() == 3
    window.close()


def test_close_waits_for_image_worker(tmp_path: Path, monkeypatch) -> None:
    from threading import Event
    from PySide6.QtCore import QThread
    application = create_application()
    window = MainWindow()
    window.show()
    page = window.images_page
    source = make_image(tmp_path / "imagem.png")
    started, release = Event(), Event()
    original = page.service.inspect
    threads = []
    def slow_inspect(path):
        threads.append(QThread.currentThread())
        started.set()
        assert release.wait(5)
        return original(path)
    monkeypatch.setattr(page.service, "inspect", slow_inspect)
    page.add_images((str(source),))
    assert started.wait(5)
    window.close()
    assert window.isVisible()
    assert not window.centralWidget().isEnabled()
    assert threads[0] != application.thread()
    release.set()
    wait(page, application)
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert not window.isVisible()
    assert page.images.count() == 0


def test_invalid_drop_and_image_recovery(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.images_page
    source = tmp_path / "quebrada.png"
    source.write_bytes(b"erro")
    page.add_images((str(source),))
    wait(page, application)
    assert page.images.count() == 0
    assert "Não foi possível" in page.status.text()
    good = make_image(tmp_path / "valida.png")
    page.add_images((str(source), str(good)))
    wait(page, application)
    assert page.images.count() == 1
    assert page.generate_button.isEnabled()
    mime = QMimeData()
    mime.setUrls([QUrl("https://example.invalid/imagem.png")])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.drop_area.dropEvent(event)
    assert not event.isAccepted()
    assert "apenas imagens locais" in page.status.text()
    page.generate_to(str(tmp_path / "ausente" / "saida.pdf"))
    wait(page, application)
    assert page.generate_button.isEnabled()
    window.close()
