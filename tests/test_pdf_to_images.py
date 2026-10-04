from pathlib import Path

from PIL import Image
from pypdf import PdfWriter
import pytest

from app.core.pdf_to_images import ExportCancelled, PdfImagesError, pdf_to_images
from tests.test_remove_pdf import make_pdf


@pytest.mark.parametrize("expression,numbers", [(None, [1, 2, 3, 4, 5]), ("3", [3]), ("2-4", [2, 3, 4]), ("1,3,5", [1, 3, 5]), ("1-3,5", [1, 2, 3, 5])])
@pytest.mark.parametrize("format,extension", [("PNG", ".png"), ("JPEG", ".jpg")])
def test_selection_names_and_formats(tmp_path: Path, expression, numbers, format, extension) -> None:
    source = tmp_path / "relatorio.pdf"
    make_pdf(source, 5)
    before = source.read_bytes()
    files = pdf_to_images(source, tmp_path, expression, format)
    assert [file.name for file in files] == [f"relatorio_pagina_{number:03}{extension}" for number in numbers]
    assert len(files) == len(numbers)
    for path in files:
        with Image.open(path) as image:
            assert image.format == format
            image.load()
    assert source.read_bytes() == before


@pytest.mark.parametrize("dpi", [96, 150, 200, 300])
@pytest.mark.parametrize("format", ["PNG", "JPEG"])
def test_single_page_dpi(tmp_path: Path, dpi: int, format: str) -> None:
    source = tmp_path / "uma.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=144, height=216)
    writer.write(source)
    result = pdf_to_images(source, tmp_path, image_format=format, dpi=dpi)
    assert len(result) == 1
    with Image.open(result[0]) as image:
        assert image.size == (dpi * 2, dpi * 3)
        assert image.info["dpi"] == pytest.approx((dpi, dpi), abs=0.02)
        if format == "PNG":
            assert image.mode == "RGBA"
            assert image.getpixel((10, 10)) == (0, 0, 0, 0)
        else:
            assert image.getpixel((10, 10)) == (255, 255, 255)


@pytest.mark.parametrize("quality", [60, 75, 90, 95])
def test_jpeg_quality(tmp_path: Path, quality: int) -> None:
    source = tmp_path / "texto.pdf"
    make_pdf(source, 1)
    path = pdf_to_images(source, tmp_path, image_format="JPEG", jpeg_quality=quality)[0]
    with Image.open(path) as actual:
        actual.load()
        assert actual.quantization


@pytest.mark.parametrize("expression", ["0", "-1", "6", "4-2", "abc", "1,,3", ""])
def test_invalid_selection(tmp_path: Path, expression: str) -> None:
    source = tmp_path / "documento.pdf"
    make_pdf(source, 5)
    with pytest.raises(PdfImagesError):
        pdf_to_images(source, tmp_path, expression)
    assert not list(tmp_path.glob("*.png"))


def test_safe_conflicts(tmp_path: Path) -> None:
    source = tmp_path / "relatorio.pdf"
    make_pdf(source, 1)
    conflict = tmp_path / "relatorio_pagina_001.png"
    conflict.write_bytes(b"existente")
    result = pdf_to_images(source, tmp_path)
    assert result[0].name == "relatorio_pagina_001_2.png"
    assert conflict.read_bytes() == b"existente"
    assert not list(tmp_path.glob(".sigilopdf-*"))


@pytest.mark.parametrize("kind", ["folder", "missing", "corrupt", "encrypted", "not_pdf", "settings"])
def test_input_errors(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "documento.pdf"
    make_pdf(source, 1)
    folder = tmp_path
    settings = {}
    if kind == "folder":
        folder = tmp_path / "ausente"
    elif kind == "missing":
        source.unlink()
    elif kind == "corrupt":
        source.write_bytes(b"invalid pdf")
    elif kind == "not_pdf":
        Image.new("RGB", (10, 10)).save(source, format="PNG")
    elif kind == "encrypted":
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt("senha")
        writer.write(source)
    else:
        settings["dpi"] = 1200
    with pytest.raises(PdfImagesError):
        pdf_to_images(source, folder, **settings)
    assert not list(tmp_path.glob("*.png"))


def test_failure_cleanup(tmp_path: Path, monkeypatch) -> None:
    import app.core.pdf_to_images as core
    source = tmp_path / "documento.pdf"
    make_pdf(source, 3)
    original = core._encode_page
    def fail_second(page, *args):
        if page.number == 1:
            raise OSError("falha simulada de renderização")
        return original(page, *args)
    monkeypatch.setattr(core, "_encode_page", fail_second)
    with pytest.raises(PdfImagesError):
        pdf_to_images(source, tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["documento.pdf"]


def test_cancellation_cleanup(tmp_path: Path) -> None:
    source = tmp_path / "documento.pdf"
    make_pdf(source, 3)
    old = tmp_path / "documento_pagina_001.png"
    old.write_bytes(b"original")
    with pytest.raises(ExportCancelled):
        pdf_to_images(source, tmp_path, cancelled=lambda: (tmp_path / "documento_pagina_001_2.png").exists())
    assert old.read_bytes() == b"original"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["documento.pdf", old.name]


def test_write_error_cleanup(tmp_path: Path, monkeypatch) -> None:
    import app.core.split_output as output
    source = tmp_path / "documento.pdf"
    make_pdf(source, 1)
    def fail(*args, **kwargs):
        raise PermissionError("falha simulada")
    monkeypatch.setattr(output.shutil, "copyfileobj", fail)
    with pytest.raises(PdfImagesError):
        pdf_to_images(source, tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["documento.pdf"]


def test_padding_for_large_document(tmp_path: Path) -> None:
    source = tmp_path / "longo.pdf"
    with PdfWriter() as writer:
        for _ in range(1000):
            writer.add_blank_page(width=72, height=72)
        writer.write(source)
    files = pdf_to_images(source, tmp_path, "1,1000", dpi=96)
    assert [path.name for path in files] == ["longo_pagina_0001.png", "longo_pagina_1000.png"]


def test_rotation_and_memory_limit(tmp_path: Path) -> None:
    source = tmp_path / "girado.pdf"
    with PdfWriter() as writer:
        writer.add_blank_page(width=144, height=216).rotate(90)
        writer.write(source)
    output = pdf_to_images(source, tmp_path, dpi=150)[0]
    with Image.open(output) as image:
        assert image.size == (450, 300)
    with PdfWriter() as writer:
        writer.add_blank_page(width=20000, height=20000)
        writer.write(source)
    with pytest.raises(PdfImagesError, match="memória excessiva"):
        pdf_to_images(source, tmp_path, dpi=300)
    assert not (tmp_path / "girado_pagina_001_2.png").exists()
