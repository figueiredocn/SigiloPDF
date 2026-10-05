from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CompressionError(Exception):
    """Falha que pode ser apresentada sem revelar conteúdo do documento."""


class CompressionCancelled(CompressionError):
    pass


class PasswordRequired(CompressionError):
    pass


class CompressionMode(Enum):
    LIGHT = "Leve"
    BALANCED = "Equilibrada"
    STRONG = "Forte"
    TARGET = "Tamanho desejado"


@dataclass(frozen=True)
class ImagePreset:
    dpi: int
    quality: int


PRESETS = {
    CompressionMode.LIGHT: ImagePreset(225, 90),
    CompressionMode.BALANCED: ImagePreset(175, 80),
    CompressionMode.STRONG: ImagePreset(125, 65),
}
TARGET_PRESETS = (ImagePreset(225, 90), ImagePreset(200, 85),
                  ImagePreset(175, 80), ImagePreset(150, 72),
                  ImagePreset(125, 65), ImagePreset(96, 50))
MAX_ATTEMPTS = 1 + len(TARGET_PRESETS)
MIN_TARGET_BYTES = 50 * 1024
MAX_TARGET_BYTES = 10 * 1024 ** 3
MIN_IMAGE_SAVING = 1024


@dataclass(frozen=True)
class CompressionOptions:
    mode: CompressionMode = CompressionMode.BALANCED
    target_size_bytes: int | None = None

    def validate(self) -> None:
        if not isinstance(self.mode, CompressionMode):
            raise CompressionError("Escolha um modo de compressão válido.")
        if self.mode == CompressionMode.TARGET:
            size = self.target_size_bytes
            if type(size) is not int or not MIN_TARGET_BYTES <= size <= MAX_TARGET_BYTES:
                raise CompressionError("Informe um tamanho entre 50 KB e 10 GB.")


@dataclass(frozen=True)
class CompressionInput:
    path: Path
    name: str
    size_bytes: int
    page_count: int
    encrypted: bool
    signed: bool
    raster_pages: int = 0
    needs_password: bool = False


@dataclass(frozen=True)
class CompressionResult:
    original_size: int
    compressed_size: int
    reduction_bytes: int
    reduction_percent: float
    output_path: Path
    target_reached: bool | None
    attempts: int
    warnings: tuple[str, ...]
    significant: bool
    target_size_bytes: int | None


def significant_reduction(original: int, compressed: int) -> bool:
    return original - compressed >= max(1024, original * 0.01)
