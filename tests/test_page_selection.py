import pytest

from app.core.page_selection import PageSelectionError, parse_page_selection


@pytest.mark.parametrize("expression,expected", [
    ("1-5", [1, 2, 3, 4, 5]),
    ("1,3,5", [1, 3, 5]),
    ("1-3,5,8-10", [1, 2, 3, 5, 8, 9, 10]),
    ("5,1,3,1,2-3", [1, 2, 3, 5]),
    (" 1 - 3 , 5 ", [1, 2, 3, 5]),
    ("01,002", [1, 2]),
])
def test_valid_selections(expression: str, expected: list[int]) -> None:
    assert parse_page_selection(expression, 20) == expected


@pytest.mark.parametrize("expression", ["0", "-1", "abc", "5-2", "1,,3", "999", "21", "", " ", "1,", ",1", "1.5", "+1", "1;3", "1-2-3", "1-", "１", "9" * 5000])
def test_invalid_selections(expression: str) -> None:
    with pytest.raises(PageSelectionError):
        parse_page_selection(expression, 20)


def test_one_page_selection() -> None:
    assert parse_page_selection("1,1-1", 1) == [1]
    with pytest.raises(PageSelectionError, match="não existe"):
        parse_page_selection("2", 1)


def test_empty_pdf_cannot_select_pages() -> None:
    with pytest.raises(PageSelectionError, match="não possui páginas"):
        parse_page_selection("1", 0)


def test_optional_input_order_does_not_change_default() -> None:
    expression = "5,1-3,2,5"
    assert parse_page_selection(expression, 10) == [1, 2, 3, 5]
    assert parse_page_selection(expression, 10, preserve_order=True) == [5, 1, 2, 3]
