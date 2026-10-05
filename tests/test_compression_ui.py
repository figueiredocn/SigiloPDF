import os
from pathlib import Path
from threading import Event
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QMimeData, QPointF, QThread, QThreadPool, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QPushButton

from app.main import create_application
from app.services.compression_service import CompressionInput
from app.ui.main_window import MainWindow
from tests.test_compression import make_pdf


def wait(page, application) -> None:
    deadline = time.monotonic() + 20
    while page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert page.worker is None


def drop(page, path: Path) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.drop_area.dropEvent(event)


def test_full_compression_flow_and_safe_save(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    card = next(button for button in window.stack.widget(0).findChildren(QPushButton) if button.text() == "Comprimir PDF")
    assert not card.icon().isNull()
    card.click()
    assert window.stack.currentIndex() == 13
    page = window.compression_page
    assert page.mode.currentText() == "Equilibrada"
    assert not page.compress_button.isEnabled()
    assert not page.save_button.isEnabled()
    source = make_pdf(tmp_path / "local.pdf", images=True)
    before = source.read_bytes()
    drop(page, source)
    assert not page.select_button.isEnabled()
    wait(page, application)
    assert "local.pdf" in page.details.text()
    assert "1 páginas" in page.details.text()
    assert page.compress_button.isEnabled()
    page.mode.setCurrentText("Tamanho desejado")
    assert page.target_panel.isEnabled()
    for text in ("0", "-5", "abc", "0,01"):
        page.target.setText(text)
        assert not page.compress_button.isEnabled()
        assert "50 KB" in page.notice.text()
    page.target.setText("2")
    page.compress_button.click()
    assert not page.mode.isEnabled()
    wait(page, application)
    assert page.result is not None
    assert page.save_button.isEnabled()
    assert "Meta atingida" in page.results.toPlainText()
    assert page.progress.value() == 100
    folder = page.result.output_path.parent
    output = tmp_path / "local_comprimido.pdf"
    output.write_bytes(b"nao substituir")
    page.save_to(str(output))
    wait(page, application)
    assert (tmp_path / "local_comprimido_2.pdf").exists()
    assert "local_comprimido_2.pdf" in page.status.text()
    assert output.read_bytes() == b"nao substituir"
    assert source.read_bytes() == before
    window.close()
    application.processEvents()
    assert not folder.exists()


def test_encrypted_input_and_secret_release(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.compression_page
    source = make_pdf(tmp_path / "senha.pdf", password="segredo")
    page.inspect_file(str(source))
    wait(page, application)
    assert page.info is None
    assert not page.password.isHidden()
    page.password.setText("errada")
    page.unlock_button.click()
    wait(page, application)
    assert "Senha incorreta" in page.status.text()
    assert not page.password.text()
    page.password.setText("segredo")
    page.unlock_button.click()
    wait(page, application)
    assert page.info.encrypted
    assert page._password == "segredo"
    page.compress_button.click()
    assert page._password is None
    assert page.password.text() == ""
    wait(page, application)
    assert page.result is not None
    window.close()
    assert page.service.preview is None


def test_close_waits_for_worker_and_slots_use_gui_thread(tmp_path: Path, monkeypatch) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    page = window.compression_page
    source = make_pdf(tmp_path / "local.pdf")
    page.inspect_file(str(source))
    wait(page, application)
    entered, release = Event(), Event()
    compress = page.service.compress
    gui_threads = []
    set_text = page.status.setText
    def record(text: str) -> None:
        gui_threads.append(QThread.currentThread())
        set_text(text)
    def delayed(*args, **kwargs):
        assert QThread.currentThread() != application.thread()
        entered.set()
        assert release.wait(5)
        return compress(*args, **kwargs)
    monkeypatch.setattr(page.status, "setText", record)
    monkeypatch.setattr(page.service, "compress", delayed)
    try:
        page.compress_button.click()
        assert entered.wait(3)
        assert not window.close()
        assert window.isVisible()
        assert not window.centralWidget().isEnabled()
        release.set()
        wait(page, application)
        deadline = time.monotonic() + 3
        while window.isVisible() and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(0.01)
        assert not window.isVisible()
        assert page.service.preview is None
        assert gui_threads and all(thread == application.thread() for thread in gui_threads)
    finally:
        release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        application.processEvents()
        window.close()


def test_input_error_recovers_and_option_change_discards_preview(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.compression_page
    page.inspect_file(str(tmp_path / "ausente.pdf"))
    wait(page, application)
    assert page.select_button.isEnabled()
    assert page.info is None
    assert not page.compress_button.isEnabled()
    source = make_pdf(tmp_path / "local.pdf")
    page.inspect_file(str(source))
    wait(page, application)
    page.compress_button.click()
    wait(page, application)
    folder = page.result.output_path.parent
    page.mode.setCurrentText("Forte")
    assert not folder.exists()
    assert page.result is None
    assert not page.save_button.isEnabled()
    assert "qualidade de imagens" in page.notice.text()
    window.close()


def test_signature_warning_blocks_processing_until_acknowledged(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    page = window.compression_page
    page.succeeded("inspect", CompressionInput(tmp_path / "assinado.pdf", "assinado.pdf", 2000, 1, False, True))
    page.update_controls()
    assert not page.signature_notice.isHidden()
    assert "invalidar" in page.signature_notice.text()
    assert not page.compress_button.isEnabled()
    page.signature.setChecked(True)
    assert page.compress_button.isEnabled()
    window.close()
    application.processEvents()


def test_cancel_button_recovers_without_output(tmp_path: Path, monkeypatch) -> None:
    application = create_application()
    window = MainWindow()
    page = window.compression_page
    source = make_pdf(tmp_path / "local.pdf")
    page.inspect_file(str(source))
    wait(page, application)
    entered, release = Event(), Event()
    compress = page.service.compress
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return compress(*args, **kwargs)
    monkeypatch.setattr(page.service, "compress", delayed)
    try:
        page.compress_button.click()
        assert entered.wait(3)
        assert page.cancel_button.isEnabled()
        page.cancel_button.click()
        release.set()
        wait(page, application)
        assert "cancelada" in page.status.text()
        assert page.result is None
        assert page.service.preview is None
        assert page.compress_button.isEnabled()
        assert not page.save_button.isEnabled()
    finally:
        release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        application.processEvents()
        window.close()


def test_compression_and_other_tool_do_not_run_concurrently(tmp_path: Path, monkeypatch) -> None:
    application = create_application()
    window = MainWindow()
    page = window.compression_page
    source = make_pdf(tmp_path / "local.pdf")
    page.inspect_file(str(source))
    wait(page, application)
    entered, release, other_entered = Event(), Event(), Event()
    compress = page.service.compress
    inspect = window.info_page.service.inspect
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return compress(*args, **kwargs)
    def other(path: str):
        other_entered.set()
        return inspect(path)
    monkeypatch.setattr(page.service, "compress", delayed)
    monkeypatch.setattr(window.info_page.service, "inspect", other)
    try:
        page.compress_button.click()
        assert entered.wait(3)
        window.info_page.inspect_file(str(source))
        assert not other_entered.wait(0.1)
        application.processEvents()
        assert window.info_page.worker is not None
        release.set()
        wait(page, application)
        wait(window.info_page, application)
        assert other_entered.is_set()
        assert window.info_page.table.rowCount() == 13
    finally:
        release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        application.processEvents()
        window.close()
