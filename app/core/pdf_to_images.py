"""Exportação local de páginas em PNG/JPEG com publicação exclusiva."""

from collections.abc import Callable
from io import BytesIO
from math import ceil
from pathlib import Path

from PIL import Image
import pymupdf

from app.core.page_selection import parse_page_selection, PageSelectionError
from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_file

JPEG_QUALITIES = {"Baixa": 60, "Média": 75, "Alta": 90, "Máxima": 95}
RESOLUTIONS = (96, 150, 200, 300)
MAX_PIXELS = 40_000_000

# Diagnósticos internos podem conter trechos do documento; a UI usa erros próprios.
pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)


class PdfImagesError(Exception):
    """Erro de exportação em pt-BR."""


class ExportCancelled(PdfImagesError):
    """Cancelamento entre páginas; saídas da operação são removidas."""


def _encode_page(page: pymupdf.Page, image_format: str, dpi: int, quality: int) -> bytes:
    scale = dpi / 72
    if ceil(page.rect.width * scale) * ceil(page.rect.height * scale) > MAX_PIXELS:
        raise PdfImagesError("Esta página exige memória excessiva na resolução escolhida. Selecione um DPI menor.")
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=image_format == "PNG")
    pixmap.set_dpi(dpi, dpi)
    if image_format == "PNG":
        return pixmap.tobytes("png")
    with Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples) as image:
        buffer = BytesIO()
        image.save(buffer, "JPEG", quality=quality, dpi=(dpi, dpi))
        return buffer.getvalue()


def pdf_to_images(pdf_path: str | Path, output_dir: str | Path, pages: str | None = None,
                  image_format: str = "PNG", dpi: int = 150, jpeg_quality: int = 90,
                  progress: Callable[[int, str], None] | None = None,
                  cancelled: Callable[[], bool] | None = None) -> list[Path]:
    report = progress or (lambda percent, text: None)
    is_cancelled = cancelled or (lambda: False)
    created: list[CreatedFile] = []
    try:
        source, folder = resolve_local_path(pdf_path), resolve_local_path(output_dir)
        if source.suffix.lower() != ".pdf":
            raise PdfImagesError("Selecione um arquivo com extensão .pdf.")
        if not folder.is_dir():
            raise PdfImagesError("A pasta de saída não existe. Escolha outra pasta.")
        if image_format not in ("PNG", "JPEG") or type(dpi) is not int or dpi not in RESOLUTIONS or type(jpeg_quality) is not int or jpeg_quality not in JPEG_QUALITIES.values():
            raise PdfImagesError("Confira o formato, a resolução e a qualidade escolhidos.")
        with pymupdf.open(source) as document:
            if not document.is_pdf:
                raise PdfImagesError("O arquivo selecionado não é um PDF válido.")
            if document.is_encrypted:
                raise PdfImagesError("Este PDF está protegido por senha.")
            if not len(document):
                raise PdfImagesError("O PDF não possui páginas para exportar.")
            selected = list(range(1, len(document) + 1)) if pages is None else parse_page_selection(pages, len(document))
            padding = max(3, len(str(len(document))))
            extension = ".png" if image_format == "PNG" else ".jpg"
            for position, page_number in enumerate(selected):
                if is_cancelled():
                    raise ExportCancelled("Exportação cancelada.")
                report(int(95 * position / len(selected)), f"Exportando página {page_number} ({position + 1} de {len(selected)})…")
                data = _encode_page(document[page_number - 1], image_format, dpi, jpeg_quality)
                basename = f"{source.stem[:100]}_pagina_{page_number:0{padding}d}"
                created.append(write_unique_file(lambda stream: stream.write(data), folder, basename, extension))
            if is_cancelled():
                raise ExportCancelled("Exportação cancelada.")
        report(100, "Exportação concluída.")
        return [path for path, _ in created]
    except (PdfImagesError, PageSelectionError, PdfInfoError) as error:
        remove_created(created)
        if isinstance(error, ExportCancelled):
            raise
        raise PdfImagesError(str(error)) from error
    except Exception as error:
        remove_created(created)
        raise PdfImagesError("Não foi possível exportar as páginas. Confira o PDF, as permissões e o espaço disponível na pasta de saída.") from error
    except BaseException:
        remove_created(created)
        raise
