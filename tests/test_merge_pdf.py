from hashlib import sha256
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app.core.merge_pdf import MergePdfError, merge_pdfs


def make_pdf(path: Path, widths: list[int], encrypted: bool = False) -> Path:
    writer = PdfWriter()
    for width in widths:
        page = writer.add_blank_page(width=width, height=300)
        content = DecodedStreamObject()
        content.set_data(f"q 0 0 {width} 20 re S Q".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
    if encrypted:
        writer.encrypt("senha")
    writer.write(path)
    return path


@pytest.fixture
def sources(tmp_path: Path) -> list[Path]:
    return [make_pdf(tmp_path / "primeiro.pdf", [101, 102]), make_pdf(tmp_path / "segundo.pdf", [201])]


def test_merge_order_progress_and_originals(sources: list[Path], tmp_path: Path) -> None:
    hashes = [sha256(path.read_bytes()).digest() for path in sources]
    progress: list[int] = []
    output = tmp_path / "resultado.pdf"
    assert merge_pdfs(sources[::-1], output, lambda percent, message: progress.append(percent)) == output
    with output.open("rb") as stream:
        reader = PdfReader(stream)
        assert [float(page.mediabox.width) for page in reader.pages] == [201, 101, 102]
        assert [page.get_contents().get_data() for page in reader.pages] == [
            b"q 0 0 201 20 re S Q", b"q 0 0 101 20 re S Q", b"q 0 0 102 20 re S Q",
        ]
    assert progress[0] == 0 and progress[-1] == 100
    assert progress == sorted(progress)
    assert hashes == [sha256(path.read_bytes()).digest() for path in sources]
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))


def test_duplicate_input_is_allowed(sources: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "duplicado.pdf"
    merge_pdfs([sources[0], sources[0]], output)
    with output.open("rb") as stream:
        assert len(PdfReader(stream).pages) == 4


@pytest.mark.parametrize("count", [0, 1])
def test_requires_multiple_files(sources: list[Path], tmp_path: Path, count: int) -> None:
    with pytest.raises(MergePdfError, match="pelo menos dois"):
        merge_pdfs(sources[:count], tmp_path / "saida.pdf")


def test_cannot_overwrite_original(sources: list[Path]) -> None:
    original = sources[0].read_bytes()
    with pytest.raises(MergePdfError, match="originais"):
        merge_pdfs(sources, sources[0])
    assert sources[0].read_bytes() == original


def test_cannot_overwrite_existing_output(sources: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "saida.pdf"
    output.write_bytes(b"arquivo existente")
    with pytest.raises(MergePdfError, match="já existe"):
        merge_pdfs(sources, output)
    assert output.read_bytes() == b"arquivo existente"


def test_output_appearing_during_merge_is_preserved(sources: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "saida.pdf"

    def race(percent: int, message: str) -> None:
        if percent == 85 and not output.exists():
            output.write_bytes(b"criado por outro processo")

    with pytest.raises(MergePdfError, match="já existe"):
        merge_pdfs(sources, output, race)
    assert output.read_bytes() == b"criado por outro processo"
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))


@pytest.mark.parametrize("kind", ["missing", "invalid", "encrypted", "empty", "extension"])
def test_bad_inputs_do_not_create_output(sources: list[Path], tmp_path: Path, kind: str) -> None:
    path = tmp_path / "problema.pdf"
    if kind == "invalid":
        path.write_bytes(b"nao e um PDF")
    elif kind == "encrypted":
        make_pdf(path, [100], encrypted=True)
    elif kind == "empty":
        make_pdf(path, [])
    elif kind == "extension":
        path = tmp_path / "arquivo.txt"
        path.write_text("texto", encoding="utf-8")
    output = tmp_path / "saida.pdf"
    with pytest.raises(MergePdfError):
        merge_pdfs([sources[0], path], output)
    assert not output.exists()
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))


def test_missing_output_directory(sources: list[Path], tmp_path: Path) -> None:
    with pytest.raises(MergePdfError, match="pasta de saída não existe"):
        merge_pdfs(sources, tmp_path / "inexistente" / "saida.pdf")


def test_remote_output_rejected(sources: list[Path]) -> None:
    with pytest.raises(MergePdfError, match="compartilhamentos de rede"):
        merge_pdfs(sources, "//servidor/compartilhamento/saida.pdf")


def test_write_failure_removes_partial_output(sources: list[Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_bytes = [path.read_bytes() for path in sources]
    output = tmp_path / "saida.pdf"

    def fail_sync(fd: int) -> None:
        raise OSError("sem espaço")

    monkeypatch.setattr("app.core.merge_pdf.os.fsync", fail_sync)
    with pytest.raises(MergePdfError, match="espaço"):
        merge_pdfs(sources, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))
    assert original_bytes == [path.read_bytes() for path in sources]


def test_generation_failure_cleans_temporary(sources: list[Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_write(self: PdfWriter, stream: object) -> None:
        stream.write(b"parcial")
        raise OSError("sem espaço")

    monkeypatch.setattr(PdfWriter, "write", fail_write)
    output = tmp_path / "saida.pdf"
    with pytest.raises(MergePdfError):
        merge_pdfs(sources, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))
