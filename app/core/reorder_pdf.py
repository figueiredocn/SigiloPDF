"""Reorganização de objetos de páginas, sem rasterização."""

from collections.abc import Callable, Sequence
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_pdf


class ReorderPdfError(Exception):
    """Erro de organização apresentado em pt-BR."""


def validate_page_order(page_order: Sequence[int], total: int) -> tuple[int, ...]:
    order = tuple(page_order)
    if not order:
        raise ReorderPdfError("Informe uma ordem que contenha todas as páginas.")
    if any(type(index) is not int or index < 0 or index >= total for index in order):
        raise ReorderPdfError("A ordem contém uma página inexistente ou inválida.")
    if len(set(order)) != len(order):
        raise ReorderPdfError("A ordem contém páginas repetidas.")
    if len(order) != total:
        raise ReorderPdfError("A ordem precisa conter todas as páginas do documento.")
    return order


def reorder_pdf(source_path: str | Path, page_order: Sequence[int], output_path: str | Path,
                progress: Callable[[int, str], None] | None = None) -> Path:
    report = progress or (lambda percent, message: None)
    created: list[CreatedFile] = []
    try:
        source, output = resolve_local_path(source_path), resolve_local_path(output_path)
        if source.suffix.lower() != ".pdf" or output.suffix.lower() != ".pdf":
            raise ReorderPdfError("Selecione arquivos com extensão .pdf.")
        if source == output:
            raise ReorderPdfError("A saída não pode ser o arquivo original. Escolha outro nome.")
        if not output.parent.is_dir():
            raise ReorderPdfError("A pasta de saída não existe. Escolha outra pasta.")
        with source.open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise ReorderPdfError("Este PDF está protegido por senha.")
            order = validate_page_order(page_order, len(reader.pages))
            with PdfWriter() as writer:
                for position, index in enumerate(order):
                    writer.add_page(reader.pages[index])
                    report(int(90 * (position + 1) / len(order)), f"Organizando página {position + 1} de {len(order)}…")
                report(95, "Salvando o PDF reorganizado…")
                created.append(write_unique_pdf(writer, output.parent, output.stem))
        report(100, "Organização concluída.")
        return created[0][0]
    except (ReorderPdfError, PdfInfoError) as error:
        remove_created(created)
        raise ReorderPdfError(str(error)) from error
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError) as error:
        remove_created(created)
        raise ReorderPdfError("Não foi possível reorganizar o PDF. Confira o arquivo, as permissões e o espaço disponível.") from error
    except BaseException:
        remove_created(created)
        raise
