from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import shutil
from typing import BinaryIO

from app.core.compression.compressor import CompressionPreview, compress_pdf
from app.core.compression.models import (CompressionCancelled, CompressionError, CompressionInput,
                                         CompressionMode, CompressionOptions, CompressionResult, PasswordRequired)
from app.core.compression.pdf_optimizer import SIGNATURE_WARNING, check_cancelled, inspect_pdf
from app.core.compression.sizes import format_size, parse_target_size
from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import write_unique_file

__all__ = ["CompressionService", "CompressionError", "CompressionCancelled", "CompressionInput",
           "CompressionMode", "CompressionOptions", "CompressionResult", "PasswordRequired",
           "SIGNATURE_WARNING", "format_size", "parse_target_size", "describe_result"]


def describe_result(result: CompressionResult) -> str:
    percent = f"{result.reduction_percent:.1f}".replace(".", ",")
    lines = [f"Original: {format_size(result.original_size)}",
             f"Comprimido: {format_size(result.compressed_size)}",
             f"Economizado: {format_size(result.reduction_bytes)} — Redução: {percent}%",
             f"Tentativas: {result.attempts}"]
    if result.target_size_bytes is not None:
        lines.extend((f"Meta: {format_size(result.target_size_bytes)}",
                      "Meta atingida" if result.target_reached else "Meta não atingida — você pode salvar o melhor resultado."))
    return "\n".join((*lines, *result.warnings))


class CompressionService:
    def __init__(self) -> None:
        self.preview: CompressionPreview | None = None
        self.source: Path | None = None

    def inspect(self, source: str, password: str | None = None) -> CompressionInput:
        return inspect_pdf(source, password)

    def compress(self, source: str, options: CompressionOptions, password: str | None,
                 allow_signed: bool, progress: Callable[[int, str], None],
                 cancelled: Callable[[], bool]) -> CompressionResult:
        if not self.release_preview():
            raise CompressionError("O sistema impediu a limpeza do resultado temporário anterior. Verifique as permissões.")
        self.source = resolve_local_path(source)
        self.preview = compress_pdf(source, options, password, allow_signed=allow_signed,
                                    progress=progress, cancelled=cancelled)
        return self.preview.result

    def save(self, output: str, progress: Callable[[int, str], None],
             cancelled: Callable[[], bool]) -> CompressionResult:
        try:
            check_cancelled(cancelled)
            if self.preview is None:
                raise CompressionError("Comprima um PDF antes de salvar.")
            destination = resolve_local_path(output)
            if destination == self.source:
                raise CompressionError("A saída não pode ser o arquivo original. Escolha outro nome.")
            if destination.suffix.lower() != ".pdf" or not destination.parent.is_dir():
                raise CompressionError("Escolha um arquivo .pdf em uma pasta local existente.")
            progress(10, "Salvando a nova cópia…")
            def copy(stream: BinaryIO) -> None:
                with self.preview.result.output_path.open("rb") as source:
                    shutil.copyfileobj(source, stream, length=1024 * 1024)
            path, _ = write_unique_file(copy, destination.parent, destination.stem, ".pdf")
            result = replace(self.preview.result, output_path=path)
            progress(100, "Nova cópia salva. O original foi preservado.")
            return result
        except CompressionError:
            raise
        except PdfInfoError as error:
            raise CompressionError(str(error)) from error
        except Exception as error:
            raise CompressionError("Não foi possível salvar. Confira a pasta, as permissões e o espaço disponível.") from error

    def release_preview(self) -> bool:
        cleaned = True
        if self.preview is not None:
            cleaned = self.preview.close()
            self.preview = None
        self.source = None
        return cleaned
