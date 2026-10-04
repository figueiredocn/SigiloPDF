"""Orientação de páginas via /Rotate, sem rasterização."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.core.extract_pdf import ExtractPdfError
from app.core.page_selection import PageSelectionError, parse_page_selection
from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_pdf


class RotatePdfError(ExtractPdfError):
    """Erro de rotação compatível com os workers de edição existentes."""


@dataclass(frozen=True)
class RotationSummary:
    pages: tuple[int, ...]
    angle: int


def summarize_rotation(expression: str, total_pages: int, angle: int, all_pages: bool) -> RotationSummary:
    if total_pages < 1:
        raise RotatePdfError("O PDF não possui páginas para girar.")
    if isinstance(angle, bool) or not isinstance(angle, int) or angle not in (90, -90, 180, 270):
        raise RotatePdfError("Escolha 90° horário, 90° anti-horário ou 180°.")
    pages = list(range(1, total_pages + 1)) if all_pages else parse_page_selection(expression, total_pages)
    return RotationSummary(tuple(pages), angle % 360)


def rotate_pages(source: str | Path, output: str | Path, angle: int, expression: str = "", *, all_pages: bool = True, progress: Callable[[int, str], None] | None = None) -> Path:
    report = progress or (lambda value, message: None)
    created: list[CreatedFile] = []
    try:
        path, destination = resolve_local_path(source), resolve_local_path(output)
        if path.suffix.lower() != ".pdf" or destination.suffix.lower() != ".pdf":
            raise RotatePdfError("Selecione arquivos com extensão .pdf para a entrada e a saída.")
        if path == destination:
            raise RotatePdfError("A saída não pode ser o arquivo original. Escolha outro nome.")
        if not destination.parent.is_dir():
            raise RotatePdfError("A pasta de saída não existe. Escolha outra pasta.")
        report(0, "Verificando o PDF localmente…")
        with path.open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise RotatePdfError("PDFs criptografados não podem ser girados nesta versão.")
            total = len(reader.pages)
            summary = summarize_rotation(expression, total, angle, all_pages)
            selected = set(summary.pages)
            writer = PdfWriter()
            last_percent = -1
            for index, page in enumerate(reader.pages, start=1):
                copied = writer.add_page(page)
                if index in selected:
                    copied.rotate(summary.angle)
                    copied.rotation = copied.rotation % 360
                percent = 10 + int(80 * index / total)
                if percent != last_percent:
                    report(percent, f"Processando página {index} de {total}…")
                    last_percent = percent
            report(90, "Salvando o PDF girado…")
            created.append(write_unique_pdf(writer, destination.parent, destination.stem))
            writer.close()
        report(100, "Rotação concluída.")
        return created[0][0]
    except (RotatePdfError, PageSelectionError, PdfInfoError) as error:
        remove_created(created)
        raise RotatePdfError(str(error)) from error
    except FileNotFoundError as error:
        remove_created(created)
        raise RotatePdfError("O PDF ou a pasta de saída não foi encontrado. Confira a seleção.") from error
    except PermissionError as error:
        remove_created(created)
        raise RotatePdfError("Sem permissão para ler o PDF ou salvar na pasta escolhida.") from error
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError) as error:
        remove_created(created)
        raise RotatePdfError("Não foi possível girar as páginas. Confira o PDF e o espaço disponível na pasta de saída.") from error
    except BaseException:
        remove_created(created)
        raise
