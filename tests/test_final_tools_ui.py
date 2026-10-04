from pathlib import Path
import time

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QTextEdit
from pypdf import PdfReader
import pytest

from app.main import create_application
from app.ui.main_window import MainWindow
from app.ui.components.about_dialog import AboutDialog, MESSAGE
from tests.test_number_pdf import source_pdf


def wait(page, application) -> None:
    deadline = time.monotonic() + 20
    while page.worker is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert page.worker is None


def drop(page, source: Path) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    page.drop_area.dropEvent(event)


def test_final_tools_flow(tmp_path: Path) -> None:
    application = create_application()
    window = MainWindow()
    window.show()
    source = source_pdf(tmp_path / "orig.pdf", 3)
    before = source.read_bytes()
    window.stack.setCurrentIndex(10)
    number = window.number_page
    drop(number, source)
    wait(number, application)
    number.first_number.setValue(10)
    number.start_page.setValue(2)
    number.format.setCurrentText("Página 1 de 20")
    number.output.setText(str(tmp_path / "numerado.pdf"))
    assert number.extract_button.isEnabled()
    number.extract_button.click()
    wait(number, application)
    reader = PdfReader(tmp_path / "numerado.pdf")
    assert reader.pages[0].extract_text().strip() == "Pagina 1"
    assert "Página 10 de 3" in reader.pages[1].extract_text()
    assert "Página 11 de 3" in reader.pages[2].extract_text()
    window.stack.setCurrentIndex(11)
    metadata = window.metadata_page
    drop(metadata, source)
    wait(metadata, application)
    metadata.fields["Título"].setText("Relatório acadêmico")
    metadata.fields["Autor"].setText("José & Ana")
    metadata.output.setText(str(tmp_path / "editado.pdf"))
    metadata.extract_button.click()
    wait(metadata, application)
    assert PdfReader(tmp_path / "editado.pdf").metadata.title == "Relatório acadêmico"
    metadata.remove_button.click()
    wait(metadata, application)
    assert PdfReader(tmp_path / "editado_2.pdf").metadata is None
    window.stack.setCurrentIndex(12)
    protection = window.protection_page
    drop(protection, source)
    wait(protection, application)
    protection.password.setText("senha-local-segura")
    protection.confirmation.setText("outra")
    assert not protection.extract_button.isEnabled()
    assert "não coincidem" in protection.summary.toPlainText()
    protection.confirmation.setText("senha-local-segura")
    protection.show_password.click()
    assert protection.show_password.text() == "Ocultar senha"
    protection.output.setText(str(tmp_path / "protegido.pdf"))
    protection.extract_button.click()
    wait(protection, application)
    assert protection.password.text() == protection.confirmation.text() == ""
    assert protection.service.password == protection.service.confirmation == ""
    reader = PdfReader(tmp_path / "protegido.pdf")
    assert reader.is_encrypted
    assert reader.decrypt("senha-local-segura") != 0
    drop(protection, tmp_path / "protegido.pdf")
    wait(protection, application)
    assert protection.mode.currentText() == "Remover proteção"
    protection.password.setText("errada")
    protection.output.setText(str(tmp_path / "aberto.pdf"))
    protection.extract_button.click()
    wait(protection, application)
    assert "Senha incorreta" in protection.status.text()
    assert protection.password.text() == ""
    assert not (tmp_path / "aberto.pdf").exists()
    protection.password.setText("senha-local-segura")
    protection.extract_button.click()
    wait(protection, application)
    assert not PdfReader(tmp_path / "aberto.pdf").is_encrypted
    assert source.read_bytes() == before
    window.close()


def test_about_and_discreet_message() -> None:
    application = create_application()
    dialog = AboutDialog()
    dialog.show()
    application.processEvents()
    assert dialog.special_dialog is None
    assert dialog.windowTitle() == "Sobre o SigiloPDF"
    for _ in range(4):
        dialog.logo.click()
    assert dialog.special_dialog is None
    dialog.logo.click()
    application.processEvents()
    assert dialog.special_dialog.isVisible()
    assert dialog.special_dialog.windowTitle() == "Por que criamos o SigiloPDF?"
    assert dialog.special_dialog.findChild(QTextEdit).toPlainText() == MESSAGE
    dialog.special_dialog.close()
    dialog.close()


@pytest.mark.parametrize("page_name", ["number_page", "metadata_page", "protection_page"])
def test_new_workers_wait_for_close(tmp_path: Path, monkeypatch, page_name: str) -> None:
    from threading import Event
    from PySide6.QtCore import QThread
    application = create_application()
    window = MainWindow()
    window.show()
    page = getattr(window, page_name)
    source = source_pdf(tmp_path / "orig.pdf", 1)
    entered, release = Event(), Event()
    inspect = page.service.inspect
    def controlled(path: str):
        assert QThread.currentThread() != application.thread()
        entered.set()
        assert release.wait(5)
        return inspect(path)
    monkeypatch.setattr(page.service, "inspect", controlled)
    page.inspect_file(str(source))
    assert entered.wait(5)
    window.close()
    assert window.isVisible()
    release.set()
    wait(page, application)
    deadline = time.monotonic() + 5
    while window.isVisible() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    assert not window.isVisible()
