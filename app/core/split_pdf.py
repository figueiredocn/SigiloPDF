"""Extração local de páginas com saídas novas e preservação do original."""

from collections.abc import Callable
from enum import Enum
from pathlib import Path
import re

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.core.page_selection import PageSelectionError, parse_page_selection, selection_label
from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_pdf

Progress = Callable[[int, str], None]


class SplitMode(str, Enum):
    EACH_PAGE = "each_page"
    RANGE = "range"
    SPECIFIC = "specific"
    COMBINATION = "combination"
    POINTS = "points"


class SplitPdfError(Exception):
    """Falha de divisão adequada para apresentação ao usuário."""


def _select_pages(mode: SplitMode, expression: str, total: int) -> list[int]:
    if mode == SplitMode.EACH_PAGE:
        return list(range(1, total + 1))
    if mode == SplitMode.RANGE and not re.fullmatch(r"\s*[0-9]+\s*-\s*[0-9]+\s*", expression):
        raise SplitPdfError("No modo Intervalo, informe um intervalo como 1-5.")
    if mode == SplitMode.SPECIFIC and "-" in expression:
        raise SplitPdfError("No modo Páginas específicas, use páginas separadas por vírgulas, como 1,3,5.")
    return parse_page_selection(expression, total)


def _extract(reader: PdfReader, groups: list[list[int]], names: list[str], folder: Path, report: Progress, created: list[CreatedFile]) -> None:
    total = sum(len(group) for group in groups)
    processed = 0
    last_percent = -1
    for index, (pages, name) in enumerate(zip(groups, names)):
        writer = PdfWriter()
        for page in pages:
            writer.add_page(reader.pages[page - 1])
            processed += 1
            percent = 10 + int(85 * processed / total)
            if percent != last_percent:
                report(percent, f"Extraindo página {page} — arquivo {index + 1} de {len(groups)}…")
                last_percent = percent
        report(last_percent, f"Salvando arquivo {index + 1} de {len(groups)}…")
        created.append(write_unique_pdf(writer, folder, name))
        writer.close()


def split_pdf(source: str | Path, output_folder: str | Path, mode: SplitMode, expression: str = "", progress: Progress | None = None) -> list[Path]:
    report = progress or (lambda percent, message: None)
    created: list[CreatedFile] = []
    try:
        mode = SplitMode(mode)
        path, folder = resolve_local_path(source), resolve_local_path(output_folder)
        if path.suffix.lower() != ".pdf":
            raise SplitPdfError("Selecione um arquivo com extensão .pdf.")
        if not folder.is_dir():
            raise SplitPdfError("A pasta de saída não existe. Escolha uma pasta válida.")
        report(0, "Verificando o PDF localmente…")
        with path.open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise SplitPdfError("PDFs criptografados não podem ser divididos nesta versão.")
            total = len(reader.pages)
            if not total:
                raise SplitPdfError("O PDF não possui páginas para dividir.")
            pages = _select_pages(mode, expression, total)
            stem = path.stem[:100]
            if mode == SplitMode.POINTS:
                if pages[-1] == total:
                    raise SplitPdfError("Marque divisões antes da última página do documento.")
                starts, ends = [1, *(page + 1 for page in pages)], [*pages, total]
                groups = [list(range(start, end + 1)) for start, end in zip(starts, ends)]
                names = [f"{stem}_parte_{index + 1:03d}_paginas_{selection_label(group)}" for index, group in enumerate(groups)]
            elif mode == SplitMode.EACH_PAGE:
                groups = [[page] for page in pages]
                digits = max(3, len(str(total)))
                names = [f"{stem}_pagina_{page:0{digits}d}" for page in pages]
            else:
                groups = [pages]
                names = [f"{stem}_paginas_{selection_label(pages)}"]
            _extract(reader, groups, names, folder, report, created)
        report(100, "Divisão concluída.")
        return [path for path, identity in created]
    except (SplitPdfError, PageSelectionError, PdfInfoError) as error:
        remove_created(created)
        raise SplitPdfError(str(error)) from error
    except FileNotFoundError as error:
        remove_created(created)
        raise SplitPdfError("O PDF ou a pasta de saída não foi encontrado. Confira a seleção.") from error
    except PermissionError as error:
        remove_created(created)
        raise SplitPdfError("Sem permissão para ler o PDF ou salvar na pasta escolhida.") from error
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError) as error:
        remove_created(created)
        raise SplitPdfError("Não foi possível dividir o PDF. Verifique o arquivo e o espaço disponível na pasta de saída.") from error
    except BaseException:
        remove_created(created)
        raise
