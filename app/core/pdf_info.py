"""Leitura de informações sem interface gráfica ou escrita no documento."""

from collections.abc import Mapping
from dataclasses import dataclass
import logging
import os
from pathlib import Path, PureWindowsPath

from pypdf import PdfReader
from pypdf.errors import PyPdfError

# O parser pode incluir bytes do documento em avisos. Não os encaminhe a logs.
_parser_logger = logging.getLogger("pypdf")
_parser_logger.addHandler(logging.NullHandler())
_parser_logger.propagate = False


class PdfInfoError(Exception):
    """Erro de leitura que pode ser apresentado ao usuário."""


@dataclass(frozen=True)
class PdfInfo:
    name: str
    path: str
    size_bytes: int
    page_count: int | None
    version: str
    title: str
    author: str
    subject: str
    producer: str
    creator: str
    creation_date: str
    modification_date: str
    encrypted: bool
    locked: bool


def _metadata_text(metadata: Mapping[str, object] | None, key: str) -> str:
    if metadata is None:
        return "Não informado"
    value = metadata.get(key)
    return str(value) if value is not None else "Não informado"


def _read_open_pdf(path: Path) -> PdfInfo:
    with path.open("rb") as stream:
        reader = PdfReader(stream, strict=False)
        encrypted = reader.is_encrypted
        locked = encrypted and not bool(reader.decrypt(""))
        metadata = None if locked else reader.metadata
        return PdfInfo(
            name=path.name, path=str(path), size_bytes=os.fstat(stream.fileno()).st_size,
            page_count=None if locked else len(reader.pages),
            version=reader.pdf_header.removeprefix("%PDF-"),
            title=_metadata_text(metadata, "/Title"),
            author=_metadata_text(metadata, "/Author"),
            subject=_metadata_text(metadata, "/Subject"),
            producer=_metadata_text(metadata, "/Producer"),
            creator=_metadata_text(metadata, "/Creator"),
            creation_date=_metadata_text(metadata, "/CreationDate"),
            modification_date=_metadata_text(metadata, "/ModDate"),
            encrypted=encrypted, locked=locked,
        )


def _ensure_local_path(path: Path) -> None:
    """Recusa compartilhamentos antes de tentar abrir ou resolver o caminho."""
    text = str(path)
    extended_local = text.startswith("\\\\?\\") and len(text) >= 7 and text[4].isalpha() and text[5:7] == ":\\"
    if text.startswith(("\\\\", "//")) and not extended_local:
        raise PdfInfoError("Selecione um PDF no seu computador, fora de compartilhamentos de rede.")
    if os.name == "nt" and path.anchor:
        import ctypes

        # O ':' após a unidade designa streams NTFS, não arquivos independentes.
        if any(":" in part for part in path.parts[1:]):
            raise PdfInfoError("Escolha um arquivo comum. Fluxos alternativos do Windows não são permitidos.")
        is_reserved = getattr(os.path, "isreserved", None)
        reserved = is_reserved(str(path)) if is_reserved else PureWindowsPath(path).is_reserved()
        if reserved:
            raise PdfInfoError("O caminho usa um nome reservado ou inválido no Windows. Escolha outro nome.")
        if ctypes.windll.kernel32.GetDriveTypeW(path.anchor) == 4:
            raise PdfInfoError("Selecione um PDF no seu computador, fora de unidades de rede.")


def resolve_local_path(filename: str | Path) -> Path:
    """Normaliza e valida caminhos locais antes de qualquer leitura ou escrita."""
    path = Path(filename).expanduser().absolute()
    _ensure_local_path(path)
    path = path.resolve()
    _ensure_local_path(path)
    return path


def read_pdf_info(filename: str | Path) -> PdfInfo:
    """Lê um PDF local; arquivos protegidos não exigem senha nesta versão."""
    try:
        path = resolve_local_path(filename)
        if path.suffix.lower() != ".pdf":
            raise PdfInfoError("Selecione um arquivo com extensão .pdf.")
        return _read_open_pdf(path)
    except PdfInfoError:
        raise
    except FileNotFoundError as error:
        raise PdfInfoError("O arquivo não foi encontrado. Selecione-o novamente.") from error
    except PermissionError as error:
        raise PdfInfoError("Sem permissão para ler o arquivo. Verifique o acesso.") from error
    except (PyPdfError, ValueError, TypeError, KeyError, OSError, RuntimeError, NotImplementedError) as error:
        raise PdfInfoError("Não foi possível ler este PDF. Ele pode estar danificado ou usar um formato de proteção incompatível.") from error
