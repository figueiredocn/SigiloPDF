from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app.core.extract_pdf import ExtractPdfError, extract_pages
from app.services.extract_pdf_service import ExtractPdfService


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "relatorio.pdf"
    writer = PdfWriter()
    for number in range(1, 11):
        page = writer.add_blank_page(width=100 + number, height=300)
        stream = DecodedStreamObject()
        stream.set_data(f"q 0 0 {number} 20 re S Q".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
        if number == 2:
            page.rotate(90)
    writer.write(path)
    return path


@pytest.mark.parametrize("expression,expected", [
    ("1", [1]), ("1,3,5", [1, 3, 5]), ("1-5", [1, 2, 3, 4, 5]),
    ("1-3,6,8-10", [1, 2, 3, 6, 8, 9, 10]), ("2-4,8", [2, 3, 4, 8]),
    ("5,1-3,2,5", [5, 1, 2, 3]),
])
def test_extract_content_order_and_original(source: Path, tmp_path: Path, expression: str, expected: list[int]) -> None:
    original = source.read_bytes()
    progress: list[int] = []
    output = tmp_path / "relatorio_extraido.pdf"
    result = extract_pages(source, output, expression, lambda value, message: progress.append(value))
    assert result == output
    with result.open("rb") as stream:
        reader = PdfReader(stream)
        assert [int(p.mediabox.width) - 100 for p in reader.pages] == expected
        assert [p.get_contents().get_data() for p in reader.pages] == [f"q 0 0 {n} 20 re S Q".encode("ascii") for n in expected]
        assert [p.rotation for p in reader.pages] == [90 if n == 2 else 0 for n in expected]
    assert source.read_bytes() == original
    assert progress == sorted(progress)
    assert progress[0] == 0 and progress[-1] == 100
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))


@pytest.mark.parametrize("expression", ["11", "0", "1,,3", "abc", "5-2", ""])
def test_invalid_selection_does_not_write(source: Path, tmp_path: Path, expression: str) -> None:
    output = tmp_path / "saida.pdf"
    with pytest.raises(ExtractPdfError):
        extract_pages(source, output, expression)
    assert not output.exists()


@pytest.mark.parametrize("password", ["senha", ""])
def test_encrypted_pdf_rejected(tmp_path: Path, password: str) -> None:
    path = tmp_path / "protegido.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt(password)
    writer.write(path)
    with pytest.raises(ExtractPdfError, match="criptografados"):
        extract_pages(path, tmp_path / "saida.pdf", "1")
    assert not (tmp_path / "saida.pdf").exists()


def test_cannot_use_original_as_destination(source: Path) -> None:
    original = source.read_bytes()
    with pytest.raises(ExtractPdfError, match="original"):
        extract_pages(source, source, "1")
    assert source.read_bytes() == original


def test_existing_outputs_are_preserved(source: Path, tmp_path: Path) -> None:
    output = tmp_path / "relatorio_extraido.pdf"
    output.write_bytes(b"preservar")
    first = extract_pages(source, output, "1")
    second = extract_pages(source, output, "1")
    assert first.name == "relatorio_extraido_2.pdf"
    assert second.name == "relatorio_extraido_3.pdf"
    assert output.read_bytes() == b"preservar"


def test_destination_race_is_safe(source: Path, tmp_path: Path) -> None:
    output = tmp_path / "saida.pdf"

    def race(value: int, message: str) -> None:
        if value == 90 and not output.exists():
            output.write_bytes(b"outro processo")

    result = extract_pages(source, output, "1", race)
    assert result.name == "saida_2.pdf"
    assert output.read_bytes() == b"outro processo"


def test_failed_write_cleans_new_output(source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_sync(fd: int) -> None:
        raise OSError("sem espaço")

    monkeypatch.setattr("app.core.split_output.os.fsync", fail_sync)
    output = tmp_path / "saida.pdf"
    with pytest.raises(ExtractPdfError, match="espaço"):
        extract_pages(source, output, "1")
    assert not output.exists()
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))


def test_remote_destination_rejected(source: Path) -> None:
    with pytest.raises(ExtractPdfError, match="compartilhamentos de rede"):
        extract_pages(source, "//servidor/pasta/saida.pdf", "1")


def test_summary_matches_extraction_order() -> None:
    summary = ExtractPdfService().summarize("5,1-3,2", 10)
    assert summary.pages == (5, 1, 2, 3)
