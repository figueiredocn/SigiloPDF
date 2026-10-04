from pathlib import Path
import os
from threading import Event
import time

import pytest
from pypdf import PdfWriter

from app.core.pdf_info import PdfInfoError, read_pdf_info


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "local.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=200)
    writer.write(path)
    return path


@pytest.mark.skipif(os.name != "nt", reason="Validação específica do Windows")
@pytest.mark.parametrize("name", ["local.pdf:conteudo.pdf", "NUL.pdf", "CON.pdf", "COM1.pdf"])
def test_windows_streams_and_device_names_are_rejected(tmp_path: Path, name: str) -> None:
    with pytest.raises(PdfInfoError, match="Windows"):
        read_pdf_info(tmp_path / name)


@pytest.mark.skipif(os.name != "nt", reason="Validação específica do Windows")
def test_windows_extended_local_path(source: Path) -> None:
    path = Path("\\\\?\\" + str(source.resolve()))
    assert read_pdf_info(path).page_count == 1


@pytest.mark.skipif(os.name != "nt", reason="Validação específica do Windows")
@pytest.mark.parametrize("operation", ["merge", "split", "extract", "remove", "rotate"])
def test_output_stream_cannot_modify_an_original(source: Path, operation: str) -> None:
    from app.core.extract_pdf import extract_pages
    from app.core.merge_pdf import merge_pdfs
    from app.core.remove_pdf import remove_pages
    from app.core.rotate_pdf import rotate_pages
    from app.core.split_pdf import SplitMode, split_pdf

    original = source.read_bytes()
    destination = str(source) + ":conteudo.pdf"
    operations = {
        "merge": lambda: merge_pdfs([source, source], destination),
        "split": lambda: split_pdf(source, destination, SplitMode.EACH_PAGE),
        "extract": lambda: extract_pages(source, destination, "1"),
        "remove": lambda: remove_pages(source, destination, "1"),
        "rotate": lambda: rotate_pages(source, destination, 90),
    }
    with pytest.raises(Exception, match="Windows"):
        operations[operation]()
    assert source.read_bytes() == original
    assert not Path(destination).exists()


@pytest.mark.parametrize("page_name", ["info_page", "merge_page", "split_page", "extract_page", "remove_page", "rotate_page"])
def test_close_waits_for_workers_and_ui_stays_in_main_thread(source: Path, page_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from PySide6.QtCore import QThread, QThreadPool
    from app.main import create_application
    from app.ui.main_window import MainWindow

    application = create_application()
    window = MainWindow()
    window.show()
    page = getattr(window, page_name)
    started, release = Event(), Event()
    inspect = page.service.inspect
    text_threads: list[object] = []
    set_status = page.status.setText

    def record_status(text: str) -> None:
        text_threads.append(QThread.currentThread())
        set_status(text)

    def delayed_inspection(path: str) -> object:
        started.set()
        assert release.wait(5)
        return inspect(path)

    monkeypatch.setattr(page.status, "setText", record_status)
    monkeypatch.setattr(page.service, "inspect", delayed_inspection)
    try:
        if page_name == "merge_page":
            page.add_files([str(source)])
        else:
            page.inspect_file(str(source))
        assert started.wait(2)
        assert not window.close()
        assert window.isVisible()
        assert not window.centralWidget().isEnabled()
        assert "Aguarde" in window.statusBar().currentMessage()
        release.set()
        deadline = time.monotonic() + 5
        while window.isVisible() and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(0.01)
        assert not window.isVisible()
        assert page.worker is None
        assert QThreadPool.globalInstance().activeThreadCount() == 0
        assert text_threads and all(thread == application.thread() for thread in text_threads)
    finally:
        release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        application.processEvents()
        window.close()


def test_tool_pages_scroll_on_small_windows() -> None:
    from PySide6.QtWidgets import QScrollArea
    from app.main import create_application
    from app.ui.main_window import MainWindow

    application = create_application()
    window = MainWindow()
    window.resize(800, 650)
    window.show()
    window.stack.setCurrentIndex(6)
    application.processEvents()
    scroll = window.stack.currentWidget()
    assert isinstance(scroll, QScrollArea)
    assert window.minimumSizeHint().height() < 768
    assert scroll.verticalScrollBar().maximum() > 0
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    application.processEvents()
    assert window.rotate_page.status.isVisibleTo(window)
    window.close()
