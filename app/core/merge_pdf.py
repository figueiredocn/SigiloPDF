"""Junção local de PDFs com criação exclusiva do arquivo de saída."""

from collections.abc import Callable, Sequence
from contextlib import ExitStack
from pathlib import Path
import os
import tempfile

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.core.pdf_info import PdfInfoError, resolve_local_path

Progress = Callable[[int, str], None]


class MergePdfError(Exception):
    """Falha de junção com mensagem adequada à interface."""


def _local_pdf_path(filename: str | Path) -> Path:
    path = resolve_local_path(filename)
    if path.suffix.lower() != ".pdf":
        raise MergePdfError("Selecione apenas arquivos com extensão .pdf.")
    return path


def _validate_paths(inputs: Sequence[str | Path], output: str | Path) -> tuple[list[Path], Path]:
    if len(inputs) < 2:
        raise MergePdfError("Adicione pelo menos dois PDFs para juntar.")
    sources = [_local_pdf_path(path) for path in inputs]
    destination = _local_pdf_path(output)
    if destination in sources:
        raise MergePdfError("A saída não pode ser um dos arquivos originais. Escolha outro nome.")
    if destination.exists():
        raise MergePdfError("O arquivo de saída já existe. Escolha outro nome para não sobrescrevê-lo.")
    if not destination.parent.is_dir():
        raise MergePdfError("A pasta de saída não existe. Escolha outra pasta.")
    return sources, destination


def _load_readers(stack: ExitStack, paths: list[Path], report: Progress) -> list[PdfReader]:
    readers: list[PdfReader] = []
    for index, path in enumerate(paths):
        stream = stack.enter_context(path.open("rb"))
        reader = PdfReader(stream, strict=False)
        if reader.is_encrypted:
            raise MergePdfError("PDFs criptografados não podem ser juntados nesta versão.")
        if not len(reader.pages):
            raise MergePdfError("Um dos PDFs não possui páginas. Remova-o da lista.")
        readers.append(reader)
        report(int(20 * (index + 1) / len(paths)), "Verificando os PDFs…")
    return readers


def _build_writer(readers: list[PdfReader], report: Progress) -> PdfWriter:
    writer = PdfWriter()
    total = sum(len(reader.pages) for reader in readers)
    processed = 0
    last_percent = -1
    for reader in readers:
        for page in reader.pages:
            writer.add_page(page)
            processed += 1
            percent = 20 + int(65 * processed / total)
            if percent != last_percent:
                report(percent, f"Juntando página {processed} de {total}…")
                last_percent = percent
    return writer


def _publish(source: Path, destination: Path, report: Progress) -> None:
    """Modo xb impede substituição inclusive se o destino surgir após a validação."""
    created = False
    identity: os.stat_result | None = None
    try:
        with destination.open("xb") as target:
            created = True
            identity = os.fstat(target.fileno())
            with source.open("rb") as stream:
                total = source.stat().st_size
                copied = 0
                while chunk := stream.read(1024 * 1024):
                    target.write(chunk)
                    copied += len(chunk)
                    report(90 + int(9 * copied / max(total, 1)), "Salvando o PDF…")
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        if created and identity is not None:
            try:
                if os.path.samestat(identity, destination.stat()):
                    destination.unlink()
            except OSError:
                pass
        raise


def merge_pdfs(inputs: Sequence[str | Path], output: str | Path, progress: Progress | None = None) -> Path:
    """Preserva a ordem e nunca substitui qualquer arquivo existente."""
    report = progress or (lambda percent, message: None)
    temporary: Path | None = None
    try:
        sources, destination = _validate_paths(inputs, output)
        report(0, "Iniciando a junção…")
        with ExitStack() as stack:
            readers = _load_readers(stack, sources, report)
            writer = _build_writer(readers, report)
            report(85, "Preparando o arquivo de saída…")
            with tempfile.NamedTemporaryFile(mode="wb", prefix=".sigilopdf-", suffix=".tmp", dir=destination.parent, delete=False) as stream:
                temporary = Path(stream.name)
                writer.write(stream)
            _publish(temporary, destination, report)
        report(100, "Junção concluída.")
        return destination
    except MergePdfError:
        raise
    except PdfInfoError as error:
        raise MergePdfError(str(error)) from error
    except FileExistsError as error:
        raise MergePdfError("O arquivo de saída já existe. Escolha outro nome para não sobrescrevê-lo.") from error
    except FileNotFoundError as error:
        raise MergePdfError("Um arquivo ou a pasta de saída não foi encontrado. Confira a seleção.") from error
    except PermissionError as error:
        raise MergePdfError("Sem permissão para ler os PDFs ou salvar na pasta escolhida.") from error
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError) as error:
        raise MergePdfError("Não foi possível juntar os PDFs. Verifique se estão íntegros e se há espaço na pasta de saída.") from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                # Preserve o resultado principal se o sistema impedir a limpeza.
                pass
