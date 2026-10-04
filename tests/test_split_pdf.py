from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app.core.split_pdf import SplitMode, SplitPdfError, split_pdf


def make_pdf(path: Path, count: int, encrypted: bool = False) -> Path:
    writer = PdfWriter()
    for number in range(1, count + 1):
        page = writer.add_blank_page(width=100 + number, height=300)
        content = DecodedStreamObject()
        content.set_data(f"q 0 0 {number} 20 re S Q".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
    if encrypted:
        writer.encrypt("senha")
    writer.write(path)
    return path


@pytest.fixture
def source(tmp_path: Path) -> Path:
    return make_pdf(tmp_path / "documento.pdf", 10)


def widths(path: Path) -> list[int]:
    with path.open("rb") as stream:
        return [int(page.mediabox.width) for page in PdfReader(stream).pages]


@pytest.mark.parametrize("mode,expression,expected,name", [
    (SplitMode.RANGE, "1-5", [101, 102, 103, 104, 105], "documento_paginas_1-5.pdf"),
    (SplitMode.SPECIFIC, "1,3,5", [101, 103, 105], "documento_paginas_1,3,5.pdf"),
    (SplitMode.COMBINATION, "1-3,5,8-10", [101, 102, 103, 105, 108, 109, 110], "documento_paginas_1-3,5,8-10.pdf"),
    (SplitMode.COMBINATION, "5,1,3,1,2-3", [101, 102, 103, 105], "documento_paginas_1-3,5.pdf"),
])
def test_selected_outputs(source: Path, tmp_path: Path, mode: SplitMode, expression: str, expected: list[int], name: str) -> None:
    original = source.read_bytes()
    progress: list[int] = []
    results = split_pdf(source, tmp_path, mode, expression, lambda percent, message: progress.append(percent))
    assert [path.name for path in results] == [name]
    assert widths(results[0]) == expected
    with results[0].open("rb") as stream:
        assert [p.get_contents().get_data() for p in PdfReader(stream).pages] == [f"q 0 0 {width - 100} 20 re S Q".encode("ascii") for width in expected]
    assert source.read_bytes() == original
    assert progress == sorted(progress)
    assert progress[0] == 0 and progress[-1] == 100
    assert not list(tmp_path.glob(".sigilopdf-*.tmp"))


def test_each_page_outputs(source: Path, tmp_path: Path) -> None:
    results = split_pdf(source, tmp_path, SplitMode.EACH_PAGE)
    assert [path.name for path in results] == [f"documento_pagina_{number:03d}.pdf" for number in range(1, 11)]
    assert [widths(path) for path in results] == [[100 + number] for number in range(1, 11)]


@pytest.mark.parametrize("mode,expression", [(SplitMode.EACH_PAGE, ""), (SplitMode.RANGE, "1-1"), (SplitMode.SPECIFIC, "1"), (SplitMode.COMBINATION, "1,1-1")])
def test_single_page_pdf(tmp_path: Path, mode: SplitMode, expression: str) -> None:
    source = make_pdf(tmp_path / "uma.pdf", 1)
    results = split_pdf(source, tmp_path, mode, expression)
    assert len(results) == 1
    assert widths(results[0]) == [101]


def test_existing_files_get_suffix_and_are_preserved(source: Path, tmp_path: Path) -> None:
    existing = tmp_path / "documento_paginas_1-5.pdf"
    existing.write_bytes(b"preservar")
    second = split_pdf(source, tmp_path, SplitMode.RANGE, "1-5")
    third = split_pdf(source, tmp_path, SplitMode.RANGE, "1-5")
    assert second[0].name == "documento_paginas_1-5_2.pdf"
    assert third[0].name == "documento_paginas_1-5_3.pdf"
    assert existing.read_bytes() == b"preservar"


def test_conflict_appearing_during_generation_is_preserved(source: Path, tmp_path: Path) -> None:
    existing = tmp_path / "documento_paginas_1-5.pdf"

    def race(percent: int, message: str) -> None:
        if percent == 95 and not existing.exists():
            existing.write_bytes(b"outro processo")

    results = split_pdf(source, tmp_path, SplitMode.RANGE, "1-5", race)
    assert results[0].name == "documento_paginas_1-5_2.pdf"
    assert existing.read_bytes() == b"outro processo"


@pytest.mark.parametrize("mode,expression", [
    (SplitMode.RANGE, "5-2"), (SplitMode.RANGE, "1,3"),
    (SplitMode.SPECIFIC, "1-3"), (SplitMode.SPECIFIC, "11"),
    (SplitMode.COMBINATION, "abc"), (SplitMode.COMBINATION, "1,,3"),
])
def test_invalid_selection_creates_nothing(source: Path, tmp_path: Path, mode: SplitMode, expression: str) -> None:
    with pytest.raises(SplitPdfError):
        split_pdf(source, tmp_path, mode, expression)
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("kind", ["missing", "invalid", "empty", "encrypted"])
def test_bad_pdf_rejected(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "erro.pdf"
    if kind == "invalid":
        source.write_bytes(b"invalido")
    elif kind in ("empty", "encrypted"):
        make_pdf(source, 0 if kind == "empty" else 1, kind == "encrypted")
    with pytest.raises(SplitPdfError):
        split_pdf(source, tmp_path, SplitMode.EACH_PAGE)
    assert not list(tmp_path.glob("*_pagina_*.pdf"))


def test_remote_folder_rejected(source: Path) -> None:
    with pytest.raises(SplitPdfError, match="compartilhamentos de rede"):
        split_pdf(source, "//servidor/pasta", SplitMode.EACH_PAGE)


def test_missing_folder_rejected(source: Path, tmp_path: Path) -> None:
    with pytest.raises(SplitPdfError, match="pasta de saída não existe"):
        split_pdf(source, tmp_path / "inexistente", SplitMode.EACH_PAGE)


def test_failure_rolls_back_new_outputs_only(source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = source.read_bytes()
    existing = tmp_path / "documento_pagina_001.pdf"
    existing.write_bytes(b"existente")
    calls = 0

    def fail_second_sync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("sem espaço")

    monkeypatch.setattr("app.core.split_output.os.fsync", fail_second_sync)
    with pytest.raises(SplitPdfError, match="espaço"):
        split_pdf(source, tmp_path, SplitMode.EACH_PAGE)
    assert set(tmp_path.iterdir()) == {source, existing}
    assert source.read_bytes() == original
    assert existing.read_bytes() == b"existente"
