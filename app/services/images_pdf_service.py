from collections.abc import Callable, Sequence
from pathlib import Path

from app.core.image_reader import ImageInfo, ImagesPdfError, inspect_image
from app.core.images_to_pdf import FIT_MODES, IMAGE_SIZE, MARGINS, ORIENTATIONS, PAGE_SIZES, images_to_pdf

__all__ = ["ImageInfo", "ImagesPdfError", "ImagesPdfService", "FIT_MODES", "IMAGE_SIZE", "MARGINS", "ORIENTATIONS", "PAGE_SIZES"]


class ImagesPdfService:
    def inspect(self, path: str) -> ImageInfo:
        return inspect_image(path)

    def generate(self, paths: Sequence[str], output: str, settings: tuple[str, str, str, str],
                 progress: Callable[[int, str], None]) -> Path:
        return images_to_pdf(paths, output, *settings, progress=progress)
