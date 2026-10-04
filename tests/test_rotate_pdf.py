from pathlib import Path
import time

import pytest
from pypdf import PdfReader, PdfWriter

from app.core.rotate_pdf import RotatePdfError, rotate_pages
from tests.test_remove_pdf import make_pdf


@pytest.fixture
def source(tmp_path: Path) -> Path:
    initial = make_pdf(tmp_path / "inicial.pdf", 6)
    writer = PdfWriter(clone_from=initial)
    writer.pages[1].rotate(90)
    writer.pages[2].rotate(270)
    path = tmp_path / "documento.pdf"
    writer.write(path)
    return path


@pytest.mark.parametrize("angle", [90, 180, -90, 270])
@pytest.mark.parametrize("all_pages,expression,selected", [(True, "", [1, 2, 3, 4, 5, 6]), (False, "1,3,5-6", [1, 3, 5, 6])])
def test_rotation_preserves_content_and_original(source: Path, tmp_path: Path, angle: int, all_pages: bool, expression: str, selected: list[int]) -> None:
    original = source.read_bytes()
    progress: list[int] = []
    result = rotate_pages(source, tmp_path / "documento_girado.pdf", angle, expression, all_pages=all_pages, progress=lambda value, message: progress.append(value))
    with source.open("rb") as original_stream, result.open("rb") as result_stream:
        before, after = PdfReader(original_stream), PdfReader(result_stream)
        assert len(after.pages) == len(before.pages)
        for number, (old, new) in enumerate(zip(before.pages, after.pages), start=1):
            assert new.rotation == ((old.rotation + angle) % 360 if number in selected else old.rotation)
            assert new.mediabox == old.mediabox
            assert new.get_contents().get_data() == old.get_contents().get_data()
            assert new.extract_text() == old.extract_text()
            assert new["/Resources"]["/XObject"]["/Im1"].get_data() == old["/Resources"]["/XObject"]["/Im1"].get_data()
            assert new["/Resources"]["/XObject"]["/Im1"]["/Width"] == 1
    assert source.read_bytes() == original
    assert progress == sorted(progress) and progress[0] == 0 and progress[-1] == 100


def test_single_page(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "unica.pdf", 1)
    result = rotate_pages(source, tmp_path / "girado.pdf", -90, "1", all_pages=False)
    with result.open("rb") as stream:
        assert PdfReader(stream).pages[0].rotation == 270


@pytest.mark.parametrize("expression", ["7", "0", "-1", "1,,3", "5-2"])
def test_invalid_selection(source: Path, tmp_path: Path, expression: str) -> None:
    output = tmp_path / "saida.pdf"
    with pytest.raises(RotatePdfError):
        rotate_pages(source, output, 90, expression, all_pages=False)
    assert not output.exists()


@pytest.mark.parametrize("angle", [0, 45, 360, 90.0, True])
def test_invalid_angle(source: Path, tmp_path: Path, angle: int) -> None:
    with pytest.raises(RotatePdfError, match="Escolha 90°"):
        rotate_pages(source, tmp_path / "saida.pdf", angle)


def test_original_and_existing_outputs_are_safe(source: Path, tmp_path: Path) -> None:
    original = source.read_bytes()
    with pytest.raises(RotatePdfError, match="original"):
        rotate_pages(source, source, 90)
    output = tmp_path / "documento_girado.pdf"
    output.write_bytes(b"preservar")
    result = rotate_pages(source, output, 90)
    assert result.name == "documento_girado_2.pdf"
    assert output.read_bytes() == b"preservar"
    assert source.read_bytes() == original


def test_encrypted_pdf_rejected(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("senha")
    source = tmp_path / "protegido.pdf"
    writer.write(source)
    with pytest.raises(RotatePdfError, match="criptografados"):
        rotate_pages(source, tmp_path / "saida.pdf", 90)


def test_write_failure_cleaned(source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(fd: int) -> None:
        raise OSError("sem espaço")

    monkeypatch.setattr("app.core.split_output.os.fsync", fail)
    output = tmp_path / "saida.pdf"
    with pytest.raises(RotatePdfError):
        rotate_pages(source, output, 90)
    assert not output.exists()
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))


def test_rotate_ui(tmp_path: Path) -> None:
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent
    from PySide6.QtWidgets import QPushButton
    from app.main import create_application
    from app.ui.main_window import MainWindow

    application = create_application()
    window = MainWindow()
    window.show()
    next(card for card in window.stack.widget(0).findChildren(QPushButton) if card.text() == "Girar páginas").click()
    assert window.stack.currentIndex() == 6
    source = make_pdf(tmp_path / "documento.pdf", 3)
    page = window.rotate_page

    def wait() -> None:
        deadline = time.monotonic() + 10
        while page.worker is not None and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(0.01)
        assert page.worker is None

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    page.drop_area.dropEvent(QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    wait()
    assert "3 página(s)" in page.details.text()
    assert "Páginas afetadas (3): 1, 2, 3" in page.summary.toPlainText()
    assert not page.expression.isEnabled()
    assert Path(page.output.text()).resolve() == (tmp_path / "documento_girado.pdf").resolve()
    page.scope.setCurrentIndex(1)
    page.expression.setText("4")
    assert not page.extract_button.isEnabled()
    page.expression.setText("1,3")
    page.direction.setCurrentIndex(page.direction.findData(-90))
    assert "90° anti-horário" in page.summary.toPlainText()
    assert "Páginas afetadas (2): 1, 3" in page.summary.toPlainText()
    page.extract_button.click()
    assert not page.direction.isEnabled()
    wait()
    assert page.progress.value() == 100
    assert "Rotação concluída" in page.status.text()
    with (tmp_path / "documento_girado.pdf").open("rb") as stream:
        assert [p.rotation for p in PdfReader(stream).pages] == [270, 0, 270]
    # Mudanças após uma operação atualizam o resumo e a configuração do próximo worker.
    page.scope.setCurrentIndex(0)
    page.direction.setCurrentIndex(page.direction.findData(180))
    page.extract_button.click()
    wait()
    with (tmp_path / "documento_girado_2.pdf").open("rb") as stream:
        assert [p.rotation for p in PdfReader(stream).pages] == [180, 180, 180]
    window.close()
    application.processEvents()
