"""Gravação exclusiva e limpeza das saídas de divisão, sem alterar a junção."""

import os
from pathlib import Path
import shutil
import tempfile
from collections.abc import Callable
from typing import BinaryIO

from pypdf import PdfWriter

CreatedFile = tuple[Path, os.stat_result]


def remove_created(files: list[CreatedFile]) -> None:
    """Remove apenas arquivos criados pela operação, quando o sistema permite."""
    for path, identity in files:
        try:
            if os.path.samestat(identity, path.stat()):
                path.unlink()
        except OSError:
            pass


def write_unique_pdf(writer: PdfWriter, folder: Path, basename: str) -> CreatedFile:
    return write_unique_file(writer.write, folder, basename, ".pdf")


def write_unique_file(write: Callable[[BinaryIO], object], folder: Path, basename: str, extension: str) -> CreatedFile:
    """Mesma publicação exclusiva para PDFs e imagens, com temporário local."""
    temporary: Path | None = None
    created: list[CreatedFile] = []
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".sigilopdf-", suffix=".tmp", dir=folder, delete=False) as stream:
            temporary = Path(stream.name)
            write(stream)
        number = 1
        while True:
            suffix = "" if number == 1 else f"_{number}"
            destination = folder / f"{basename}{suffix}{extension}"
            try:
                target = destination.open("xb")
            except FileExistsError:
                number += 1
                continue
            with target:
                identity = os.fstat(target.fileno())
                created.append((destination, identity))
                with temporary.open("rb") as source:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            return destination, identity
    except BaseException:
        remove_created(created)
        raise
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
