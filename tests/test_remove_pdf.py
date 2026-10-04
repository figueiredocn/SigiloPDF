from pathlib import Path
import time

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from app.core.remove_pdf import ALL_PAGES_MESSAGE, RemovePdfError, remove_pages


def make_pdf(path: Path, count: int) -> Path:
    writer = PdfWriter()
    for number in range(1, count + 1):
        page = writer.add_blank_page(width=100 + number, height=300)
        image = DecodedStreamObject()
        image.set_data(b"\xff\x00\x00")
        image.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"), NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1), NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}), NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): writer._add_object(image)})})
        content = DecodedStreamObject()
        content.set_data(f"q 0 0 {number} 20 re S Q BT /F1 12 Tf 10 30 Td (Pagina {number}) Tj ET q 10 0 0 10 0 0 cm /Im1 Do Q".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
    writer.write(path)
    return path


@pytest.mark.parametrize("expression,expected", [
    ("2", [1, 3, 4, 5, 6]), ("2,4,6", [1, 3, 5]),
    ("1-3", [4, 5, 6]), ("1", [2, 3, 4, 5, 6]),
    ("6", [1, 2, 3, 4, 5]), ("1-2,5", [3, 4, 6]),
])
def test_removal_preserves_original_content(tmp_path: Path, expression: str, expected: list[int]) -> None:
    source = make_pdf(tmp_path / "contrato.pdf", 6)
    original = source.read_bytes()
    output = tmp_path / "contrato_sem_paginas.pdf"
    progress: list[int] = []
    result = remove_pages(source, output, expression, lambda value, message: progress.append(value))
    with source.open("rb") as original_stream, result.open("rb") as result_stream:
        before, after = PdfReader(original_stream), PdfReader(result_stream)
        assert [int(p.mediabox.width) - 100 for p in after.pages] == expected
        for page, number in zip(after.pages, expected):
            assert page.get_contents().get_data() == before.pages[number - 1].get_contents().get_data()
            assert page.extract_text().strip() == f"Pagina {number}"
            assert page["/Resources"]["/XObject"]["/Im1"].get_data() == b"\xff\x00\x00"
            assert page["/Resources"]["/Font"]["/F1"]["/BaseFont"] == "/Helvetica"
    assert source.read_bytes() == original
    assert progress == sorted(progress) and progress[-1] == 100


@pytest.mark.parametrize("count,expression", [(6, "1-6"), (6, "6,1-5,1"), (1, "1")])
def test_cannot_remove_all_pages(tmp_path: Path, count: int, expression: str) -> None:
    source = make_pdf(tmp_path / "contrato.pdf", count)
    output = tmp_path / "saida.pdf"
    with pytest.raises(RemovePdfError) as caught:
        remove_pages(source, output, expression)
    assert str(caught.value) == ALL_PAGES_MESSAGE
    assert not output.exists()


@pytest.mark.parametrize("expression", ["0", "-1", "7", "abc", "1,,3"])
def test_invalid_page_rejected(tmp_path: Path, expression: str) -> None:
    source = make_pdf(tmp_path / "contrato.pdf", 6)
    with pytest.raises(RemovePdfError):
        remove_pages(source, tmp_path / "saida.pdf", expression)
    assert not (tmp_path / "saida.pdf").exists()


def test_original_and_existing_outputs_are_safe(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "contrato.pdf", 3)
    original = source.read_bytes()
    with pytest.raises(RemovePdfError, match="original"):
        remove_pages(source, source, "2")
    assert source.read_bytes() == original
    output = tmp_path / "saida.pdf"
    output.write_bytes(b"preservar")
    result = remove_pages(source, output, "2")
    assert result.name == "saida_2.pdf"
    assert output.read_bytes() == b"preservar"


def test_failed_write_is_cleaned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = make_pdf(tmp_path / "contrato.pdf", 3)

    def fail(fd: int) -> None:
        raise OSError("sem espaço")

    monkeypatch.setattr("app.core.split_output.os.fsync", fail)
    with pytest.raises(RemovePdfError):
        remove_pages(source, tmp_path / "saida.pdf", "2")
    assert set(tmp_path.iterdir()) == {source}


def test_remove_ui(tmp_path: Path) -> None:
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent
    from PySide6.QtWidgets import QPushButton
    from app.main import create_application
    from app.ui.main_window import MainWindow

    application = create_application()
    window = MainWindow()
    window.show()
    next(card for card in window.stack.widget(0).findChildren(QPushButton) if card.text() == "Remover páginas").click()
    assert window.stack.currentIndex() == 5
    source = make_pdf(tmp_path / "contrato.pdf", 4)
    original = source.read_bytes()
    page = window.remove_page

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
    assert "4 página(s)" in page.details.text()
    assert Path(page.output.text()).resolve() == (tmp_path / "contrato_sem_paginas.pdf").resolve()
    page.expression.setText("1-4")
    assert page.summary.toPlainText() == ALL_PAGES_MESSAGE
    assert not page.extract_button.isEnabled()
    page.expression.setText("2,4")
    assert "Remover 2 página(s): 2, 4" in page.summary.toPlainText()
    assert "Manter 2 página(s): 1, 3" in page.summary.toPlainText()
    page.extract_button.click()
    assert not page.expression.isEnabled()
    wait()
    assert page.progress.value() == 100
    assert "Remoção concluída" in page.status.text()
    with (tmp_path / "contrato_sem_paginas.pdf").open("rb") as stream:
        assert [int(p.mediabox.width) - 100 for p in PdfReader(stream).pages] == [1, 3]
    assert source.read_bytes() == original
    window.close()
    application.processEvents()
