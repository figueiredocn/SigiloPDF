from pathlib import Path

from pypdf import PdfWriter
import pytest

from app.core.pdf_edit import PdfEditError
from app.core.number_pdf import number_pdf
from app.core.pdf_metadata import edit_metadata
from app.core.pdf_protection import protect_pdf
from tests.test_remove_pdf import make_pdf

OPERATIONS = (
    lambda source, output: number_pdf(source, output),
    lambda source, output: edit_metadata(source, output, {"Autor": "Teste"}),
    lambda source, output: protect_pdf(source, output, "senha", "senha"),
)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_common_write_failure_cleanup(tmp_path: Path, monkeypatch, operation) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 1)
    before = source.read_bytes()
    def fail(*args, **kwargs):
        raise PermissionError("falha simulada")
    monkeypatch.setattr(PdfWriter, "write", fail)
    with pytest.raises(PdfEditError):
        operation(source, tmp_path / "saida.pdf")
    assert source.read_bytes() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["original.pdf"]


@pytest.mark.parametrize("operation", OPERATIONS)
def test_common_input_errors(tmp_path: Path, operation) -> None:
    with pytest.raises(PdfEditError):
        operation(tmp_path / "ausente.pdf", tmp_path / "saida.pdf")
    source = tmp_path / "quebrado.pdf"
    source.write_bytes(b"PDF invalido")
    with pytest.raises(PdfEditError):
        operation(source, tmp_path / "saida.pdf")
    assert not (tmp_path / "saida.pdf").exists()
