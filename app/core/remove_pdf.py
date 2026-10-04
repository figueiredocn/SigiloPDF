"""Remoção local de páginas, sem rasterização ou alteração do original."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.core.extract_pdf import ExtractPdfError
from app.core.page_selection import PageSelectionError, parse_page_selection
from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_pdf

ALL_PAGES_MESSAGE = "Um documento PDF precisa manter pelo menos uma página."


class RemovePdfError(ExtractPdfError):
    """Erro de edição de páginas compatível com os workers existentes."""


@dataclass(frozen=True)
class RemovalSummary:
    removed: tuple[int, ...]
    remaining: tuple[int, ...]


def summarize_removal(expression: str, total_pages: int) -> RemovalSummary:
    removed = parse_page_selection(expression, total_pages)
    if len(removed) == total_pages:
        raise RemovePdfError(ALL_PAGES_MESSAGE)
    excluded = set(removed)
    return RemovalSummary(tuple(removed), tuple(page for page in range(1, total_pages + 1) if page not in excluded))


def remove_pages(source: str | Path, output: str | Path, expression: str, progress: Callable[[int, str], None] | None = None) -> Path:
    report = progress or (lambda value, message: None)
    created: list[CreatedFile] = []
    try:
        path, destination = resolve_local_path(source), resolve_local_path(output)
        if path.suffix.lower() != ".pdf" or destination.suffix.lower() != ".pdf":
            raise RemovePdfError("Selecione arquivos com extensão .pdf para a entrada e a saída.")
        if path == destination:
            raise RemovePdfError("A saída não pode ser o arquivo original. Escolha outro nome.")
        if not destination.parent.is_dir():
            raise RemovePdfError("A pasta de saída não existe. Escolha outra pasta.")
        report(0, "Verificando o PDF localmente…")
        with path.open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise RemovePdfError("PDFs criptografados não podem ter páginas removidas nesta versão.")
            summary = summarize_removal(expression, len(reader.pages))
            writer = PdfWriter()
            last_percent = -1
            for index, page in enumerate(summary.remaining):
                writer.add_page(reader.pages[page - 1])
                percent = 10 + int(80 * (index + 1) / len(summary.remaining))
                if percent != last_percent:
                    report(percent, f"Preservando página {page} ({index + 1} de {len(summary.remaining)})…")
                    last_percent = percent
            report(90, "Salvando o PDF sem as páginas selecionadas…")
            created.append(write_unique_pdf(writer, destination.parent, destination.stem))
            writer.close()
        report(100, "Remoção concluída.")
        return created[0][0]
    except (RemovePdfError, PageSelectionError, PdfInfoError) as error:
        remove_created(created)
        raise RemovePdfError(str(error)) from error
    except FileNotFoundError as error:
        remove_created(created)
        raise RemovePdfError("O PDF ou a pasta de saída não foi encontrado. Confira a seleção.") from error
    except PermissionError as error:
        remove_created(created)
        raise RemovePdfError("Sem permissão para ler o PDF ou salvar na pasta escolhida.") from error
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError) as error:
        remove_created(created)
        raise RemovePdfError("Não foi possível remover as páginas. Confira o PDF e o espaço disponível na pasta de saída.") from error
    except BaseException:
        remove_created(created)
        raise
