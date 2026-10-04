"""Leitura e miniaturas de imagens locais sem dependência de Qt."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import warnings

from PIL import Image, ImageOps

from app.core.pdf_info import resolve_local_path

SUPPORTED = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".bmp": "BMP"}


class ImagesPdfError(Exception):
    """Erro de leitura ou conversão apresentado em pt-BR."""


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    width: int
    height: int
    size_bytes: int
    thumbnail: bytes


def open_image(path: str | Path) -> Image.Image:
    local = resolve_local_path(path)
    if local.suffix.lower() not in SUPPORTED:
        raise ImagesPdfError("Formato não suportado. Selecione JPG, JPEG, PNG ou BMP.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        image = Image.open(local)
    if image.format != SUPPORTED[local.suffix.lower()]:
        image.close()
        raise ImagesPdfError("O conteúdo da imagem não corresponde ao formato do arquivo.")
    return image


def white_background(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", image.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image if image.mode in ("RGB", "L") else image.convert("RGB")


def inspect_image(path: str | Path) -> ImageInfo:
    try:
        local = resolve_local_path(path)
        with open_image(local) as image:
            width, height = image.size
            if image.getexif().get(274, 1) in (5, 6, 7, 8):
                width, height = height, width
            # JPEG pode reduzir a decodificação antes de carregar os pixels.
            image.draft("RGB", (180, 180))
            image.thumbnail((180, 180))
            thumbnail = white_background(ImageOps.exif_transpose(image))
            buffer = BytesIO()
            thumbnail.save(buffer, format="PNG")
            return ImageInfo(local, width, height, local.stat().st_size, buffer.getvalue())
    except ImagesPdfError:
        raise
    except Exception as error:
        raise ImagesPdfError("Não foi possível ler a imagem. Confira o formato, a integridade e as permissões do arquivo.") from error
