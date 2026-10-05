from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory, gettempdir

from app.core.compression.image_optimizer import optimize_images
from app.core.compression.models import (CompressionError, CompressionInput, CompressionMode,
                                         CompressionOptions, CompressionResult, ImagePreset, PRESETS,
                                         TARGET_PRESETS, significant_reduction)
from app.core.compression.pdf_optimizer import (SIGNATURE_WARNING, check_cancelled, inspect_pdf,
                                                open_pdf, save_optimized, verify_pdf)
from app.core.pdf_info import resolve_local_path


@dataclass
class CompressionPreview:
    result: CompressionResult
    temporary: TemporaryDirectory

    def close(self) -> bool:
        return _cleanup(self.temporary)


def _cleanup(temporary: TemporaryDirectory | None) -> bool:
    try:
        if temporary is not None:
            temporary.cleanup()
        return True
    except OSError:
        return False


def _candidates(options: CompressionOptions) -> tuple[ImagePreset | None, ...]:
    if options.mode == CompressionMode.TARGET:
        return (None, *TARGET_PRESETS)
    return (None, PRESETS[options.mode])


def _attempt(info: CompressionInput, candidate: Path, preset: ImagePreset | None, password: str | None,
             progress: Callable[[int, str], None], cancelled: Callable[[], bool]) -> int:
    with open_pdf(info.path, password) as document:
        skipped = optimize_images(document, preset, progress, cancelled) if preset is not None else 0
        check_cancelled(cancelled)
        progress(95, "Comprimindo a estrutura do PDF…")
        save_optimized(document, candidate)
    check_cancelled(cancelled)
    verify_pdf(candidate, info.page_count, password)
    return skipped


def compress_pdf(source: str | Path, options: CompressionOptions = CompressionOptions(),
                 password: str | None = None, *, allow_signed: bool = False,
                 progress: Callable[[int, str], None] = lambda value, message: None,
                 cancelled: Callable[[], bool] = lambda: False) -> CompressionPreview:
    temporary: TemporaryDirectory | None = None
    try:
        options.validate()
        check_cancelled(cancelled)
        progress(0, "Analisando documento…")
        info = inspect_pdf(source, password)
        if info.signed and not allow_signed:
            raise CompressionError(SIGNATURE_WARNING + " Confirme o aviso antes de continuar.")
        temporary = TemporaryDirectory(prefix="sigilopdf-compressao-", dir=resolve_local_path(gettempdir()))
        folder = Path(temporary.name)
        best, best_size, attempts, skipped = info.path, info.size_bytes, 0, 0
        candidates = _candidates(options)
        target = options.target_size_bytes if options.mode == CompressionMode.TARGET else None
        for index, preset in enumerate(candidates):
            check_cancelled(cancelled)
            candidate = folder / f"tentativa_{index + 1}.pdf"
            progress(index * 90 // len(candidates), f"Tentativa {index + 1} de {len(candidates)}…")
            def attempt_progress(value: int, message: str) -> None:
                percent = int(90 * (index + value / 100) / len(candidates))
                progress(percent, f"Tentativa {index + 1} de {len(candidates)} — {message}")
            skipped = max(skipped, _attempt(info, candidate, preset, password, attempt_progress, cancelled))
            attempts += 1
            size = candidate.stat().st_size
            if size < best_size:
                if best != info.path:
                    best.unlink()
                best, best_size = candidate, size
            else:
                candidate.unlink()
            if target is not None and best_size <= target:
                break
            if options.mode == CompressionMode.LIGHT and significant_reduction(info.size_bytes, best_size):
                break
        check_cancelled(cancelled)
        progress(95, "Finalizando arquivo…")
        final = folder / "resultado.pdf"
        if best == info.path:
            shutil.copyfile(info.path, final)
        else:
            best.replace(final)
        verify_pdf(final, info.page_count, password)
        warnings = _warnings(info, best_size, target, skipped)
        saved = info.size_bytes - best_size
        result = CompressionResult(info.size_bytes, best_size, saved, 100 * saved / info.size_bytes,
                                   final, best_size <= target if target is not None else None,
                                   attempts, warnings, significant_reduction(info.size_bytes, best_size), target)
        check_cancelled(cancelled)
        progress(100, "Compressão concluída. Escolha onde salvar a nova cópia.")
        return CompressionPreview(result, temporary)
    except CompressionError as error:
        if not _cleanup(temporary):
            raise CompressionError(str(error) + " O sistema impediu a limpeza dos temporários.") from error
        raise
    except BaseException as error:
        cleaned = _cleanup(temporary)
        if not isinstance(error, Exception):
            raise
        message = "Não foi possível comprimir este PDF. Confira o arquivo, as permissões e o espaço disponível."
        if not cleaned:
            message += " O sistema impediu a limpeza dos temporários."
        raise CompressionError(message) from error


def _warnings(info: CompressionInput, size: int, target: int | None, skipped: int) -> tuple[str, ...]:
    warnings: list[str] = []
    if not significant_reduction(info.size_bytes, size):
        warnings.append("Este PDF já parece estar bem otimizado. Não houve redução significativa.")
    if target is not None and size > target:
        warnings.append("Não foi possível atingir o tamanho solicitado mantendo os limites mínimos de qualidade.")
    if skipped:
        warnings.append("Algumas imagens foram preservadas por segurança ou por excederem o limite de processamento por imagem.")
    if info.signed and size < info.size_bytes:
        warnings.append(SIGNATURE_WARNING)
    return tuple(warnings)
