"""Numeração vetorial sobre páginas originais, reutilizando o parser."""

from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pymupdf
from pypdf import PdfReader, PdfWriter, Transformation

from app.core.page_selection import PageSelectionError, parse_page_selection
from app.core.pdf_edit import PdfEditError, copy_and_edit

POSITIONS = ("Superior esquerdo", "Superior central", "Superior direito", "Inferior esquerdo", "Inferior central", "Inferior direito")
FORMATS = ("1", "Página 1", "1 de 20", "Página 1 de 20")
FONT_SIZES = {"Pequeno": 9, "Médio": 12, "Grande": 16}


@dataclass(frozen=True)
class NumberSettings:
    expression: str | None = None
    first_number: int = 1
    start_page: int = 1
    format: str = "1"
    position: str = "Inferior central"
    size: str = "Médio"


def selected_number_pages(settings: NumberSettings, total: int) -> list[int]:
    if type(settings.first_number) is not int or settings.first_number < 0:
        raise PdfEditError("O número inicial deve ser um inteiro maior ou igual a zero.")
    if type(settings.start_page) is not int or not 1 <= settings.start_page <= total:
        raise PdfEditError("A página inicial da numeração não existe no documento.")
    if settings.format not in FORMATS or settings.position not in POSITIONS or settings.size not in FONT_SIZES:
        raise PdfEditError("Confira o formato, a posição e o tamanho da numeração.")
    try:
        pages = list(range(1, total + 1)) if settings.expression is None else parse_page_selection(settings.expression, total)
    except PageSelectionError as error:
        raise PdfEditError(str(error)) from error
    selected = [page for page in pages if page >= settings.start_page]
    if not selected:
        raise PdfEditError("Nenhuma página selecionada está após a página inicial da numeração.")
    return selected


def number_label(number: int, total: int, format: str) -> str:
    label = f"Página {number}" if format.startswith("Página") else str(number)
    return f"{label} de {total}" if " de " in format else label


def _overlay(width: float, height: float, label: str, settings: NumberSettings) -> bytes:
    font = FONT_SIZES[settings.size]
    margin = 18
    text_width = pymupdf.Font("helv").text_length(label, fontsize=font)
    if width < text_width + 2 * margin or height < 2 * margin + font:
        raise PdfEditError("A numeração não cabe nesta página com margem segura. Escolha um tamanho menor.")
    x = margin if settings.position.endswith("esquerdo") else width - margin - text_width if settings.position.endswith("direito") else (width - text_width) / 2
    y = margin + font if settings.position.startswith("Superior") else height - margin
    with pymupdf.open() as document:
        page = document.new_page(width=width, height=height)
        page.insert_text((x, y), label, fontsize=font, fontname="helv", color=(0, 0, 0))
        return document.tobytes()


def number_pdf(source: str | Path, output: str | Path, settings: NumberSettings = NumberSettings(),
               progress: Callable[[int, str], None] | None = None) -> Path:
    report = progress or (lambda value, text: None)
    def edit(writer: PdfWriter) -> None:
        total = len(writer.pages)
        selected = selected_number_pages(settings, total)
        for offset, number in enumerate(selected):
            page = writer.pages[number - 1]
            if page.rotation:
                page.transfer_rotation_to_content()
            box = page.cropbox
            label = number_label(settings.first_number + offset, total, settings.format)
            overlay = PdfReader(BytesIO(_overlay(float(box.width), float(box.height), label, settings)))
            page.merge_transformed_page(overlay.pages[0], Transformation().translate(float(box.left), float(box.bottom)))
            report(int(90 * (offset + 1) / len(selected)), f"Numerando página {number} ({offset + 1} de {len(selected)})…")
        report(95, "Salvando o PDF numerado…")
    result = copy_and_edit(source, output, edit)
    report(100, "Numeração concluída.")
    return result
