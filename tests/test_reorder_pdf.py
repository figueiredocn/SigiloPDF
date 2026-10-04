from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
import pymupdf

from app.core.reorder_pdf import ReorderPdfError, reorder_pdf
from app.core.pdf_thumbnails import render_thumbnails
from app.services.reorder_pdf_service import ReorderPdfService
from tests.test_remove_pdf import make_pdf


@pytest.mark.parametrize("order", [[0, 1, 2, 3, 4], [4, 0, 1, 2, 3], [4, 3, 2, 1, 0], [1, 0, 2, 3, 4]])
def test_reorder_preserves_content(tmp_path: Path, order: list[int]) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 5)
    before = source.read_bytes()
    original = PdfReader(source)
    progress = []
    result = reorder_pdf(source, order, tmp_path / "saida.pdf", lambda value, text: progress.append(value))
    pages = PdfReader(result).pages
    assert len(pages) == 5
    for position, index in enumerate(order):
        assert pages[position].get_contents().get_data() == original.pages[index].get_contents().get_data()
        assert pages[position].extract_text() == original.pages[index].extract_text()
        assert pages[position].images[0].data == original.pages[index].images[0].data
    assert source.read_bytes() == before
    assert progress[-1] == 100


@pytest.mark.parametrize("order", [[], [0, 0, 1, 2, 3], [0, 1, 2, 3, 5], [0, 1], [-1, 0, 1, 2, 3], [True, 1, 2, 3, 4]])
def test_invalid_order(tmp_path: Path, order: list[int]) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 5)
    output = tmp_path / "saida.pdf"
    with pytest.raises(ReorderPdfError):
        reorder_pdf(source, order, output)
    assert not output.exists()


def test_single_page_and_safe_names(tmp_path: Path) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 1)
    before = source.read_bytes()
    with pytest.raises(ReorderPdfError, match="original"):
        reorder_pdf(source, [0], source)
    output = tmp_path / "saida.pdf"
    output.write_bytes(b"existente")
    result = reorder_pdf(source, [0], output)
    assert result.name == "saida_2.pdf"
    assert len(PdfReader(result).pages) == 1
    assert output.read_bytes() == b"existente"
    assert source.read_bytes() == before
    assert not list(tmp_path.glob(".sigilopdf-*"))


def test_encrypted(tmp_path: Path) -> None:
    source = tmp_path / "senha.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("senha")
    writer.write(source)
    with pytest.raises(ReorderPdfError, match="Este PDF está protegido por senha"):
        reorder_pdf(source, [0], tmp_path / "saida.pdf")
    with pytest.raises(ReorderPdfError, match="Este PDF está protegido por senha"):
        ReorderPdfService().inspect(str(source))


def test_thumbnails_and_cancellation(tmp_path: Path) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 10)
    received = []
    render_thumbnails(source, lambda index, data: received.append((index, data)), lambda: len(received) == 3)
    assert [index for index, _ in received] == [0, 1, 2]
    for _, data in received:
        pixmap = pymupdf.Pixmap(data)
        assert max(pixmap.width, pixmap.height) <= 181
    assert sorted(path.name for path in tmp_path.iterdir()) == ["original.pdf"]


def test_write_failure_cleans_files(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 1)
    def fail(*args, **kwargs):
        raise OSError("falha simulada")
    monkeypatch.setattr(PdfWriter, "write", fail)
    with pytest.raises(ReorderPdfError):
        reorder_pdf(source, [0], tmp_path / "saida.pdf")
    assert [path.name for path in tmp_path.iterdir()] == ["original.pdf"]
