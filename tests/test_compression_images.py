from io import BytesIO
from pathlib import Path
from random import Random

from PIL import Image
import pymupdf

from app.core.compression.compressor import compress_pdf
from app.core.compression.image_optimizer import optimize_images
from app.core.compression.models import ImagePreset


def test_transparency_is_preserved(tmp_path: Path) -> None:
    source = tmp_path / "transparencia.pdf"
    with Image.new("RGBA", (400, 400), (255, 0, 0, 100)) as image:
        buffer = BytesIO()
        image.save(buffer, "PNG")
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_image(page.rect, stream=buffer.getvalue())
        document.save(source)
    with pymupdf.open(source) as document:
        original_pixels = document[0].get_pixmap().samples
    preview = compress_pdf(source)
    try:
        with pymupdf.open(preview.result.output_path) as document:
            assert document[0].get_pixmap().samples == original_pixels
        assert any("preservadas" in text for text in preview.result.warnings)
    finally:
        preview.close()


def test_low_dpi_is_not_upsampled_and_icc_is_retained() -> None:
    with Image.frombytes("RGB", (200, 200), Random(1).randbytes(120000)) as image:
        buffer = BytesIO()
        image.save(buffer, "PNG")
    with pymupdf.open() as document:
        page = document.new_page()
        xref = page.insert_image(page.rect, stream=buffer.getvalue())
        color = document.xref_get_key(xref, "ColorSpace")
        optimize_images(document, ImagePreset(175, 80), lambda *_: None, lambda: False)
        assert document.xref_get_key(xref, "Width")[1] == "200"
        assert document.xref_get_key(xref, "Height")[1] == "200"
        assert document.xref_get_key(xref, "ColorSpace") == color


def test_no_recompression_when_jpeg_would_be_larger() -> None:
    with Image.new("RGB", (100, 100), "white") as image:
        buffer = BytesIO()
        image.save(buffer, "JPEG", quality=50)
    with pymupdf.open() as document:
        page = document.new_page()
        xref = page.insert_image(page.rect, stream=buffer.getvalue())
        original = document.xref_stream_raw(xref)
        optimize_images(document, ImagePreset(175, 90), lambda *_: None, lambda: False)
        assert document.xref_stream_raw(xref) == original


def test_shared_image_respects_largest_placement() -> None:
    with Image.frombytes("RGB", (1200, 1200), Random(1).randbytes(1200 * 1200 * 3)) as image:
        buffer = BytesIO()
        image.save(buffer, "PNG")
    with pymupdf.open() as document:
        first = document.new_page()
        xref = first.insert_image(pymupdf.Rect(0, 0, 100, 100), stream=buffer.getvalue())
        second = document.new_page()
        second.insert_image(pymupdf.Rect(0, 0, 500, 500), xref=xref)
        optimize_images(document, ImagePreset(96, 50), lambda *_: None, lambda: False)
        width = int(document.xref_get_key(xref, "Width")[1])
        assert 665 <= width <= 668
