from decimal import Decimal, InvalidOperation

from app.core.compression.models import CompressionError, MAX_TARGET_BYTES, MIN_TARGET_BYTES


def format_size(size: int) -> str:
    value = float(size)
    unit = "B"
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            break
        value /= 1024
    return f"{value:.2f}".replace(".", ",") + f" {unit}"


def parse_target_size(text: str, unit: str) -> int:
    try:
        value = Decimal(text.strip().replace(",", "."))
        if unit not in ("KB", "MB") or not value.is_finite() or value <= 0:
            raise ValueError
        size = int(value * (1024 if unit == "KB" else 1024 ** 2))
        if not MIN_TARGET_BYTES <= size <= MAX_TARGET_BYTES:
            raise ValueError
        return size
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise CompressionError("Informe um tamanho válido entre 50 KB e 10 GB, usando KB ou MB.") from error
