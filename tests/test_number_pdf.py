from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
import pymupdf
import pytest

from app.core.number_pdf import FORMATS, POSITIONS, NumberSettings, number_pdf
from app.core.pdf_edit import PdfEditError
from tests.test_remove_pdf import make_pdf


def source_pdf(path: Path, count: int = 5) -> Path:
    make_pdf(path, count)
    reader = PdfReader(path)
    writer = PdfWriter(clone_from=reader)
    for page in writer.pages:
        page.mediabox = RectangleObject((0, 0, 500, 600))
    writer.write(path.with_name("amplo.pdf"))
    return path.with_name("amplo.pdf")


@pytest.mark.parametrize("settings,pages,labels", [
    (NumberSettings(), [1, 2, 3, 4, 5], ["1", "2", "3", "4", "5"]),
    (NumberSettings(expression="2-4"), [2, 3, 4], ["1", "2", "3"]),
    (NumberSettings(expression="3", first_number=100), [3], ["100"]),
    (NumberSettings(start_page=2, first_number=10), [2, 3, 4, 5], ["10", "11", "12", "13"]),
    (NumberSettings(expression="1,3,5", start_page=3), [3, 5], ["1", "2"]),
])
def test_numbering(tmp_path: Path, settings, pages, labels) -> None:
    source = source_pdf(tmp_path / "orig.pdf")
    before = source.read_bytes()
    result = number_pdf(source, tmp_path / "numerado.pdf", settings)
    reader, original = PdfReader(result), PdfReader(source)
    assert len(reader.pages) == 5
    for index, page in enumerate(reader.pages, 1):
        assert f"Pagina {index}" in page.extract_text()
        if index in pages:
            assert page.extract_text().splitlines()[-1] == labels[pages.index(index)]
        else:
            assert page.get_contents().get_data() == original.pages[index - 1].get_contents().get_data()
        assert page.images[0].data == original.pages[index - 1].images[0].data
    assert source.read_bytes() == before


@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize("format", FORMATS)
def test_positions_and_formats(tmp_path: Path, position: str, format: str) -> None:
    source = source_pdf(tmp_path / "orig.pdf", 1)
    result = number_pdf(source, tmp_path / "saida.pdf", NumberSettings(position=position, format=format))
    expected = ("Página " if format.startswith("Página") else "") + "1" + (" de 1" if " de " in format else "")
    with pymupdf.open(result) as document:
        matches = document[0].search_for(expected)
        assert matches
        box = matches[-1]
        if position.startswith("Superior"):
            assert box.y0 < 40
        else:
            assert box.y0 > 550
        if position.endswith("esquerdo"):
            assert box.x0 == pytest.approx(18, abs=0.1)
        elif position.endswith("direito"):
            assert box.x1 == pytest.approx(482, abs=0.1)
        else:
            assert (box.x0 + box.x1) / 2 == pytest.approx(250, abs=0.1)


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_rotated_and_cropped_pages(tmp_path: Path, rotation: int) -> None:
    source = source_pdf(tmp_path / "orig.pdf", 1)
    writer = PdfWriter(clone_from=PdfReader(source))
    writer.pages[0].cropbox = RectangleObject((5, 10, 495, 590))
    writer.pages[0].rotate(rotation)
    writer.write(tmp_path / "girado.pdf")
    result = number_pdf(tmp_path / "girado.pdf", tmp_path / "num.pdf", NumberSettings(format="Página 1"))
    with pymupdf.open(result) as final, pymupdf.open(tmp_path / "girado.pdf") as original:
        assert final[0].rect == original[0].rect
        assert "Página 1" in final[0].get_text()
        assert "Pagina 1" in final[0].get_text()


@pytest.mark.parametrize("settings", [NumberSettings(expression="999"), NumberSettings(expression="0"), NumberSettings(start_page=6), NumberSettings(first_number=-1), NumberSettings(expression="1", start_page=2)])
def test_invalid_numbering(tmp_path: Path, settings) -> None:
    source = source_pdf(tmp_path / "orig.pdf")
    with pytest.raises(PdfEditError):
        number_pdf(source, tmp_path / "erro.pdf", settings)
    assert not (tmp_path / "erro.pdf").exists()


def test_safe_output(tmp_path: Path) -> None:
    source = source_pdf(tmp_path / "orig.pdf", 1)
    with pytest.raises(PdfEditError, match="original"):
        number_pdf(source, source)
    output = tmp_path / "saida.pdf"
    output.write_bytes(b"existente")
    result = number_pdf(source, output)
    assert result.name == "saida_2.pdf"
    assert output.read_bytes() == b"existente"
