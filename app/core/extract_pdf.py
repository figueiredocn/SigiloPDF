"""Extração de páginas sem rasterização, reutilizando parser e escrita segura."""

from collections.abc import Callable
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.core.page_selection import PageSelectionError, parse_page_selection
from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_pdf


class ExtractPdfError(Exception):
    """Falha de extração com mensagem para o usuário."""


def extract_pages(source: str | Path, output: str | Path, expression: str, progress: Callable[[int, str], None] | None = None) -> Path:
    report = progress or (lambda percent, message: None)
    created: list[CreatedFile] = []
    try:
        path, destination = resolve_local_path(source), resolve_local_path(output)
        if path.suffix.lower() != ".pdf" or destination.suffix.lower() != ".pdf":
            raise ExtractPdfError("Selecione arquivos com extensão .pdf para a entrada e a saída.")
        if path == destination:
            raise ExtractPdfError("A saída não pode ser o arquivo original. Escolha outro nome.")
        if not destination.parent.is_dir():
            raise ExtractPdfError("A pasta de saída não existe. Escolha outra pasta.")
        report(0, "Verificando o PDF localmente…")
        with path.open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise ExtractPdfError("PDFs criptografados não podem ser extraídos nesta versão.")
            pages = parse_page_selection(expression, len(reader.pages), preserve_order=True)
            writer = PdfWriter()
            last_percent = -1
            for index, page in enumerate(pages):
                writer.add_page(reader.pages[page - 1])
                percent = 10 + int(80 * (index + 1) / len(pages))
                if percent != last_percent:
                    report(percent, f"Extraindo página {page} ({index + 1} de {len(pages)})…")
                    last_percent = percent
            report(90, "Salvando o PDF extraído…")
            created.append(write_unique_pdf(writer, destination.parent, destination.stem))
            writer.close()
        report(100, "Extração concluída.")
        return created[0][0]
    except (ExtractPdfError, PageSelectionError, PdfInfoError) as error:
        remove_created(created)
        raise ExtractPdfError(str(error)) from error
    except FileNotFoundError as error:
        remove_created(created)
        raise ExtractPdfError("O PDF ou a pasta de saída não foi encontrado. Confira a seleção.") from error
    except PermissionError as error:
        remove_created(created)
        raise ExtractPdfError("Sem permissão para ler o PDF ou salvar na pasta escolhida.") from error
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError) as error:
        remove_created(created)
        raise ExtractPdfError("Não foi possível extrair as páginas. Confira o PDF e o espaço disponível na pasta de saída.") from error
    except BaseException:
        remove_created(created)
        raise
