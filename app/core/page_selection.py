"""Parser de páginas em numeração humana (iniciada em 1), sem dependência de UI."""

import re


class PageSelectionError(ValueError):
    """Seleção inválida com explicação em português."""


def _page_number(value: str, total_pages: int) -> int:
    digits = value.lstrip("0") or "0"
    if len(digits) > len(str(total_pages)):
        raise PageSelectionError(f"O PDF possui apenas {total_pages} página(s). Confira a seleção.")
    page = int(digits)
    if not 1 <= page <= total_pages:
        raise PageSelectionError(f"Escolha páginas entre 1 e {total_pages}. A página {page} não existe neste PDF.")
    return page


def parse_page_selection(text: str, total_pages: int, *, preserve_order: bool = False) -> list[int]:
    """Retorna páginas únicas; opcionalmente preserva a ordem informada."""
    if total_pages < 1:
        raise PageSelectionError("O PDF não possui páginas para selecionar.")
    if not text.strip():
        raise PageSelectionError("Informe as páginas ou intervalos desejados.")
    pages: set[int] = set()
    ordered: list[int] = []
    for token in text.split(","):
        match = re.fullmatch(r"\s*([0-9]+)\s*(?:-\s*([0-9]+)\s*)?", token)
        if match is None:
            raise PageSelectionError("Seleção inválida. Use números, vírgulas e intervalos, como 1-3,5,8-10, sem itens vazios.")
        start = _page_number(match.group(1), total_pages)
        end = _page_number(match.group(2), total_pages) if match.group(2) else start
        if end < start:
            raise PageSelectionError("Intervalo invertido. A página inicial deve ser menor ou igual à final, como 2-5.")
        if preserve_order:
            for page in range(start, end + 1):
                if page not in pages:
                    pages.add(page)
                    ordered.append(page)
        else:
            pages.update(range(start, end + 1))
    return ordered if preserve_order else sorted(pages)


def selection_label(pages: list[int], max_length: int | None = 80) -> str:
    """Compacta uma seleção ordenada para compor nomes curtos e legíveis."""
    groups: list[str] = []
    if not pages:
        return ""
    start = previous = pages[0]
    for page in pages[1:]:
        if page != previous + 1:
            groups.append(str(start) if start == previous else f"{start}-{previous}")
            start = page
        previous = page
    groups.append(str(start) if start == previous else f"{start}-{previous}")
    label = ",".join(groups)
    return label if max_length is None or len(label) <= max_length else f"selecionadas_{len(pages)}"
