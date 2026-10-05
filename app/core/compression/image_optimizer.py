from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from math import hypot
import re

from PIL import Image
import pymupdf

from app.core.compression.models import ImagePreset, MIN_IMAGE_SAVING
from app.core.compression.pdf_optimizer import check_cancelled

MAX_IMAGE_PIXELS = 25_000_000


@dataclass
class ImageUsage:
    page: int
    width_points: float
    height_points: float


def image_usages(document: pymupdf.Document, cancelled: Callable[[], bool]) -> dict[int, ImageUsage]:
    usages: dict[int, ImageUsage] = {}
    for page in document:
        check_cancelled(cancelled)
        placements: dict[tuple[int, int], tuple[float, float]] = {}
        # Não calcular hashes de pixels: isso decodificaria todos os recursos.
        # Dimensões iguais usam a maior ocorrência como limite conservador.
        for image in page.get_image_info(hashes=False, xrefs=False):
            a, b, c, d, _, _ = image["transform"]
            width, height = hypot(a, b), hypot(c, d)
            if width <= 0 or height <= 0:
                continue
            dimensions = (image["width"], image["height"])
            previous = placements.get(dimensions, (0.0, 0.0))
            placements[dimensions] = (max(width, previous[0]), max(height, previous[1]))
        for image in page.get_images(full=True):
            xref = image[0]
            dimensions = (image[2], image[3])
            if dimensions not in placements:
                continue  # Recursos sem ocorrência e imagens inline não são alterados.
            width, height = placements[dimensions]
            current = usages.get(xref)
            if current is None:
                usages[xref] = ImageUsage(page.number, width, height)
            else:
                current.width_points = max(current.width_points, width)
                current.height_points = max(current.height_points, height)
    return usages


def supported_image(document: pymupdf.Document, xref: int) -> bool:
    for key in ("SMask", "Mask", "Decode", "Alternates"):
        if document.xref_get_key(xref, key)[0] != "null":
            return False
    if document.xref_get_key(xref, "ImageMask")[1] == "true":
        return False
    if document.xref_get_key(xref, "SMaskInData")[1] not in ("null", "0"):
        return False
    kind, color = document.xref_get_key(xref, "ColorSpace")
    if kind == "xref":
        color = document.xref_object(int(color.split()[0]))
    profile = re.fullmatch(r"\[\s*/ICCBased\s+(\d+)\s+0\s+R\s*\]", color.strip())
    supported = color.strip() in ("/DeviceRGB", "/DeviceGray")
    if profile:
        supported = document.xref_get_key(int(profile[1]), "N")[1] in ("1", "3")
    return supported and document.xref_get_key(xref, "BitsPerComponent")[1] == "8"


def optimized_jpeg(data: bytes, usage: ImageUsage, preset: ImagePreset) -> bytes | None:
    with Image.open(BytesIO(data)) as image:
        if image.width * image.height > MAX_IMAGE_PIXELS or image.mode not in ("RGB", "L"):
            return None
        scale = min(1.0, max(preset.dpi * usage.width_points / (72 * image.width),
                             preset.dpi * usage.height_points / (72 * image.height)))
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image.load()
        resized = image.resize(size, Image.Resampling.LANCZOS) if size != image.size else image.copy()
        try:
            buffer = BytesIO()
            # Huffman optimize com BytesIO pode exceder o buffer do encoder
            # em imagens ruidosas. A codificação normal escreve em blocos.
            resized.save(buffer, "JPEG", quality=preset.quality, optimize=False, subsampling=0)
            return buffer.getvalue()
        finally:
            resized.close()


def optimize_images(document: pymupdf.Document, preset: ImagePreset,
                    progress: Callable[[int, str], None], cancelled: Callable[[], bool]) -> int:
    usages = image_usages(document, cancelled)
    skipped = 0
    for number, (xref, usage) in enumerate(usages.items(), 1):
        check_cancelled(cancelled)
        progress(number * 100 // max(1, len(usages)), f"Otimizando imagem {number} de {len(usages)}…")
        if not supported_image(document, xref):
            skipped += 1
            continue
        width = int(document.xref_get_key(xref, "Width")[1])
        height = int(document.xref_get_key(xref, "Height")[1])
        if width * height > MAX_IMAGE_PIXELS:
            skipped += 1
            continue
        original = document.extract_image(xref)
        if not original:
            skipped += 1
            continue
        try:
            replacement = optimized_jpeg(original["image"], usage, preset)
        except (OSError, ValueError, Image.DecompressionBombError):
            skipped += 1
            continue
        encoded_size = len(document.xref_stream_raw(xref))
        if replacement is not None and encoded_size - len(replacement) >= max(MIN_IMAGE_SAVING, encoded_size * 0.01):
            _replace_stream(document, xref, replacement)
    return skipped


def _replace_stream(document: pymupdf.Document, xref: int, jpeg: bytes) -> None:
    # Alterar somente o recurso evita as referências duplicadas criadas por
    # Page.replace_image. ColorSpace, ICC, conteúdo e propriedades são mantidos.
    with Image.open(BytesIO(jpeg)) as image:
        width, height = image.size
    document.update_stream(xref, jpeg, compress=False)
    document.xref_set_key(xref, "Filter", "/DCTDecode")
    document.xref_set_key(xref, "DecodeParms", "null")
    document.xref_set_key(xref, "Width", str(width))
    document.xref_set_key(xref, "Height", str(height))
