from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from app.core.image_reader import ImagesPdfError, inspect_image
from app.core.images_to_pdf import IMAGE_SIZE, images_to_pdf, page_geometry


def make_image(path: Path, size: tuple[int, int] = (120, 200), mode: str = "RGB", color="red") -> Path:
    Image.new(mode, size, color).save(path)
    return path


@pytest.mark.parametrize("extension", ["jpg", "jpeg", "png", "bmp"])
def test_formats(tmp_path: Path, extension: str) -> None:
    source = make_image(tmp_path / f"imagem.{extension}")
    before = source.read_bytes()
    result = images_to_pdf([source], tmp_path / "saida.pdf")
    assert len(PdfReader(result).pages) == 1
    assert source.read_bytes() == before
    info = inspect_image(source)
    assert (info.width, info.height) == (120, 200)
    assert info.size_bytes == len(before)
    assert info.thumbnail.startswith(b"\x89PNG")


def test_order_and_page_count(tmp_path: Path) -> None:
    paths = [make_image(tmp_path / f"{index}.png", (100 + index, 200)) for index in range(5)]
    paths = paths[::-1]
    result = images_to_pdf(paths, tmp_path / "saida.pdf")
    pages = PdfReader(result).pages
    assert len(pages) == 5
    assert [page["/Resources"]["/XObject"]["/Imagem"]["/Width"] for page in pages] == [104, 103, 102, 101, 100]


@pytest.mark.parametrize("size,orientation,landscape", [((120, 200), "Automática", False), ((200, 120), "Automática", True), ((200, 120), "Retrato", False), ((120, 200), "Paisagem", True)])
@pytest.mark.parametrize("page_size,points", [("A4", (595.276, 841.89)), ("A3", (841.89, 1190.551)), ("Carta", (612, 792))])
def test_paper_and_orientation(tmp_path: Path, size, orientation, landscape, page_size, points) -> None:
    source = make_image(tmp_path / "imagem.png", size)
    page = PdfReader(images_to_pdf([source], tmp_path / "saida.pdf", page_size, orientation)).pages[0]
    dimensions = (float(page.mediabox.width), float(page.mediabox.height))
    assert dimensions == pytest.approx(points[::-1] if landscape else points)


@pytest.mark.parametrize("mode,color", [("RGB", (12, 34, 56)), ("RGBA", (0, 0, 0, 0)), ("L", 127), ("LA", (0, 0)), ("P", 0)])
def test_color_and_transparency(tmp_path: Path, mode: str, color) -> None:
    source = make_image(tmp_path / "imagem.png", (10, 10), mode, color)
    reader = PdfReader(images_to_pdf([source], tmp_path / "saida.pdf"))
    image = reader.pages[0].images[0].image
    if mode in ("RGBA", "LA"):
        assert image.convert("RGB").getpixel((5, 5)) == (255, 255, 255)
    elif mode == "RGB":
        assert image.getpixel((5, 5)) == color
    elif mode == "L":
        assert image.getpixel((5, 5)) == 127


def test_jpeg_preserved(tmp_path: Path) -> None:
    source = make_image(tmp_path / "imagem.jpg")
    page = PdfReader(images_to_pdf([source], tmp_path / "saida.pdf")).pages[0]
    xobject = page["/Resources"]["/XObject"]["/Imagem"]
    assert xobject["/Filter"] == "/DCTDecode"
    assert xobject._data == source.read_bytes()


def test_exif_orientation(tmp_path: Path) -> None:
    source = tmp_path / "orientada.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (100, 200), "red").save(source, exif=exif)
    info = inspect_image(source)
    assert (info.width, info.height) == (200, 100)
    page = PdfReader(images_to_pdf([source], tmp_path / "saida.pdf")).pages[0]
    assert page.mediabox.width > page.mediabox.height
    assert page["/Resources"]["/XObject"]["/Imagem"]["/Width"] == 200


@pytest.mark.parametrize("fit", ["Ajustar à página", "Preencher página", "Tamanho original"])
@pytest.mark.parametrize("margin", ["Sem margem", "Pequena", "Média", "Grande"])
def test_geometry(fit: str, margin: str) -> None:
    pw, ph, dw, dh, x, y, border = page_geometry(200, 100, (96, 96), "A4", "Retrato", fit, margin)
    assert dw / dh == pytest.approx(2)
    assert x == pytest.approx((pw - dw) / 2)
    assert y == pytest.approx((ph - dh) / 2)
    if fit == "Ajustar à página":
        assert dw <= pw - border * 2 + 0.001 and dh <= ph - border * 2 + 0.001
    elif fit == "Preencher página":
        assert dw >= pw - border * 2 - 0.001 and dh >= ph - border * 2 - 0.001
    else:
        assert (dw, dh) == (150, 75)


def test_image_page_dpi(tmp_path: Path) -> None:
    source = tmp_path / "dpi.png"
    Image.new("RGB", (300, 600), "red").save(source, dpi=(300, 300))
    page = PdfReader(images_to_pdf([source], tmp_path / "saida.pdf", IMAGE_SIZE, margin="Sem margem")).pages[0]
    assert float(page.mediabox.width) == pytest.approx(72, abs=0.01)
    assert float(page.mediabox.height) == pytest.approx(144, abs=0.01)


@pytest.mark.parametrize("kind", ["missing", "corrupt", "unsupported", "mismatch", "empty"])
def test_invalid_images(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "imagem.png"
    if kind == "corrupt":
        source.write_bytes(b"imagem invalida")
    elif kind == "unsupported":
        source = tmp_path / "imagem.gif"
        make_image(source)
    elif kind == "mismatch":
        Image.new("RGB", (10, 10)).save(source, format="JPEG")
    output = tmp_path / "saida.pdf"
    with pytest.raises(ImagesPdfError):
        images_to_pdf([] if kind == "empty" else [source], output)
    assert not output.exists()
    assert not list(tmp_path.glob(".sigilopdf-*"))


def test_safe_output_and_original(tmp_path: Path) -> None:
    source = make_image(tmp_path / "imagem.png")
    before = source.read_bytes()
    output = tmp_path / "saida.pdf"
    output.write_bytes(b"existente")
    result = images_to_pdf([source], output)
    assert result.name == "saida_2.pdf"
    assert output.read_bytes() == b"existente"
    with pytest.raises(ImagesPdfError, match="original"):
        images_to_pdf([source], source)
    assert source.read_bytes() == before


def test_write_failure(tmp_path: Path, monkeypatch) -> None:
    source = make_image(tmp_path / "imagem.png")
    def fail(*args, **kwargs):
        raise PermissionError("falha simulada")
    monkeypatch.setattr(PdfWriter, "write", fail)
    with pytest.raises(ImagesPdfError):
        images_to_pdf([source], tmp_path / "saida.pdf")
    assert [path.name for path in tmp_path.iterdir()] == ["imagem.png"]
