from collections.abc import Callable
from pathlib import Path

import pymupdf

from app.core.compression.models import CompressionCancelled, CompressionError, CompressionInput, PasswordRequired
from app.core.pdf_info import PdfInfoError, resolve_local_path

SIGNATURE_WARNING = "Este documento pode conter assinatura digital. Alterações no PDF podem invalidar a assinatura."
pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)


def check_cancelled(cancelled: Callable[[], bool]) -> None:
    if cancelled():
        raise CompressionCancelled("Compressão cancelada. O arquivo original foi preservado.")


def open_pdf(source: str | Path, password: str | None) -> pymupdf.Document:
    document: pymupdf.Document | None = None
    try:
        path = resolve_local_path(source)
        if path.suffix.lower() != ".pdf":
            raise CompressionError("Selecione um arquivo com extensão .pdf.")
        document = pymupdf.open(path)
        if not document.is_pdf:
            raise CompressionError("O arquivo selecionado não é um PDF válido.")
        if document.needs_pass:
            if password is None:
                raise PasswordRequired("Este PDF está protegido. Informe a senha para continuar.")
            if not document.authenticate(password):
                raise CompressionError("Senha incorreta. Confira a senha atual do PDF.")
        if document.page_count < 1:
            raise CompressionError("O PDF precisa conter pelo menos uma página.")
        return document
    except BaseException:
        if document is not None:
            document.close()
        raise


def has_signatures(document: pymupdf.Document) -> bool:
    if document.get_sigflags() > 0:
        return True
    for index in range(1, document.xref_length()):
        if document.xref_get_key(index, "FT") == ("name", "/Sig"):
            return True
        if document.xref_get_key(index, "Type") == ("name", "/Sig"):
            return True
    return False


def inspect_pdf(source: str | Path, password: str | None = None) -> CompressionInput:
    try:
        path = resolve_local_path(source)
        with open_pdf(path, password) as document:
            encrypted = document.metadata.get("encryption") is not None
            raster_pages = _raster_pages(document)
            return CompressionInput(path, path.name, path.stat().st_size,
                                    document.page_count, encrypted, has_signatures(document), raster_pages,
                                    bool(document.needs_pass))
    except CompressionError:
        raise
    except PdfInfoError as error:
        raise CompressionError(str(error)) from error
    except Exception as error:
        raise CompressionError("Não foi possível ler este PDF. Confira o arquivo e as permissões de acesso.") from error


def _raster_pages(document: pymupdf.Document) -> int:
    count = 0
    for page in document:
        area = page.rect.get_area()
        if area and any((pymupdf.Rect(image["bbox"]) & page.rect).get_area() >= 0.8 * area
                        for image in page.get_image_info(hashes=False)):
            count += 1
    return count


def save_optimized(document: pymupdf.Document, destination: Path) -> None:
    # Não limpar conteúdos, achatar formulários ou alterar metadados.
    document.save(destination, garbage=3, deflate=True, deflate_images=True,
                  deflate_fonts=True, use_objstms=1, compression_effort=6,
                  encryption=pymupdf.PDF_ENCRYPT_KEEP, no_new_id=True)


def verify_pdf(path: Path, pages: int, password: str | None) -> None:
    with open_pdf(path, password) as document:
        if document.page_count != pages:
            raise CompressionError("A verificação do PDF falhou. Nenhuma saída foi salva.")
