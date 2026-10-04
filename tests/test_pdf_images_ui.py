from pathlib import Path
import time

from PIL import Image
import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDropEvent

from app.main import create_application
from app.ui.main_window import MainWindow
from tests.test_remove_pdf import make_pdf


def wait(page, application) -> None:
    deadline = time.monotonic() + 60
    while page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert page.worker is None


def test_export_flow(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    window.stack.setCurrentIndex(9)
    page = window.pdf_images_page
    source = tmp_path / "texto.pdf"
    make_pdf(source, 5)
    before = source.read_bytes()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    page.drop_area.dropEvent(QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    wait(page, application)
    assert page.loaded == 5
    assert page.image_format.currentText() == "PNG"
    assert page.resolution.currentText() == "150 DPI"
    assert not page.quality.isEnabled()
    assert all(not page.pages.item(row).icon().isNull() for row in range(5))
    png_folder = tmp_path / "png"
    png_folder.mkdir()
    page.folder.setText(str(png_folder))
    page.start_export()
    wait(page, application)
    files = sorted(png_folder.iterdir())
    assert len(files) == 5
    with Image.open(files[0]) as image:
        assert image.size == (211, 625)
        assert image.getextrema()[3][1] == 255  # Há texto/vetores opacos sobre transparência.
    jpeg_folder = tmp_path / "jpeg"
    jpeg_folder.mkdir()
    page.folder.setText(str(jpeg_folder))
    page.image_format.setCurrentText("JPEG")
    assert page.quality.isEnabled()
    page.resolution.setCurrentText("300 DPI")
    page.quality.setCurrentText("Alta")
    page.selection_mode.setCurrentIndex(2)
    page.expression.setText("1,3,5")
    page.start_export()
    wait(page, application)
    files = sorted(jpeg_folder.iterdir())
    assert [file.name for file in files] == ["texto_pagina_001.jpg", "texto_pagina_003.jpg", "texto_pagina_005.jpg"]
    with Image.open(files[0]) as image:
        assert image.size == (421, 1250)
        assert image.getpixel((400, 100)) == (255, 255, 255)
    assert str(files[0].resolve()) in page.results.toPlainText()
    page.expression.setText("999")
    page.start_export()
    wait(page, application)
    assert page.export_button.isEnabled()
    assert "página" in page.status.text().lower()
    assert source.read_bytes() == before
    window.close()


def test_fifty_pages_responsive(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    page = window.pdf_images_page
    source = tmp_path / "cinquenta.pdf"
    make_pdf(source, 50)
    page.inspect_file(str(source))
    wait(page, application)
    folder = tmp_path / "saida"
    folder.mkdir()
    page.folder.setText(str(folder))
    ticks = []
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: ticks.append(page.worker is not None))
    timer.start()
    page.start_export()
    wait(page, application)
    timer.stop()
    assert any(ticks)
    assert len(list(folder.glob("*.png"))) == 50
    assert page.progress.value() == 100
    window.close()


@pytest.mark.parametrize("closing", [False, True])
def test_cancel_export(tmp_path: Path, monkeypatch, closing: bool) -> None:
    from threading import Event
    from app.core.pdf_to_images import ExportCancelled
    application = create_application()
    window = MainWindow()
    window.show()
    page = window.pdf_images_page
    source = tmp_path / "documento.pdf"
    make_pdf(source, 1)
    page.inspect_file(str(source))
    wait(page, application)
    entered = Event()
    def controlled(*args):
        entered.set()
        deadline = time.monotonic() + 5
        while not args[-1]() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert args[-1]()
        raise ExportCancelled("Exportação cancelada.")
    monkeypatch.setattr(page.service, "export", controlled)
    page.folder.setText(str(tmp_path))
    page.start_export()
    assert entered.wait(5)
    if closing:
        window.close()
        assert window.isVisible()
    else:
        page.cancel_button.click()
    wait(page, application)
    assert "cancelada" in page.status.text()
    assert not page.cancel_button.isEnabled()
    if closing:
        deadline = time.monotonic() + 5
        while window.isVisible() and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(0.01)
        assert not window.isVisible()
    window.close()
