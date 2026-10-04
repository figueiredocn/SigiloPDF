"""Metadados comuns: leitura, edição e remoção de Info/XMP."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.core.pdf_edit import PdfEditError, copy_and_edit
from app.core.pdf_info import PdfInfo, read_pdf_info, resolve_local_path

EDITABLE_FIELDS = {"Título": "/Title", "Autor": "/Author", "Assunto": "/Subject", "Palavras-chave": "/Keywords"}
ANONYMITY_WARNING = "A remoção de metadados reduz informações incorporadas ao documento, mas não garante anonimização completa do arquivo."


@dataclass(frozen=True)
class MetadataSnapshot:
    info: PdfInfo
    fields: dict[str, str]


def read_metadata(source: str | Path) -> MetadataSnapshot:
    try:
        info = read_pdf_info(source)
        if info.encrypted:
            return MetadataSnapshot(info, {label: "" for label in EDITABLE_FIELDS})
        with resolve_local_path(source).open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            metadata = reader.metadata or {}
            fields = {label: "" if metadata.get(key) is None else str(metadata[key]) for label, key in EDITABLE_FIELDS.items()}
            xmp = reader.xmp_metadata
            if xmp is not None:
                fallback = ((xmp.dc_title or {}).get("x-default", ""), ", ".join(xmp.dc_creator or []),
                            (xmp.dc_description or {}).get("x-default", ""), xmp.pdf_keywords or "")
                for label, value in zip(EDITABLE_FIELDS, fallback):
                    if not fields[label]:
                        fields[label] = value
            return MetadataSnapshot(info, fields)
    except PdfEditError:
        raise
    except Exception as error:
        raise PdfEditError("Não foi possível ler os metadados deste PDF.") from error


def edit_metadata(source: str | Path, output: str | Path, fields: dict[str, str], *, clear: bool = False) -> Path:
    def edit(writer: PdfWriter) -> None:
        if clear:
            writer.metadata = None
            writer.xmp_metadata = None
            for page in writer.pages:
                page.pop("/Metadata", None)
            writer._ID = None
        else:
            if any(label not in EDITABLE_FIELDS or not isinstance(value, str) for label, value in fields.items()):
                raise PdfEditError("Informe somente os campos de metadados editáveis.")
            writer.add_metadata({EDITABLE_FIELDS[label]: value for label, value in fields.items()})
            xmp = writer.xmp_metadata
            if xmp is not None:
                if "Título" in fields:
                    xmp.dc_title = {"x-default": fields["Título"]}
                if "Autor" in fields:
                    xmp.dc_creator = [fields["Autor"]] if fields["Autor"] else []
                if "Assunto" in fields:
                    xmp.dc_description = {"x-default": fields["Assunto"]}
                if "Palavras-chave" in fields:
                    xmp.pdf_keywords = fields["Palavras-chave"]
                writer.xmp_metadata = xmp
        # Não serializar Info/XMP antigos que ficaram sem referência.
        writer.compress_identical_objects()
    return copy_and_edit(source, output, edit)
