from pathlib import Path

from pypdf import PdfReader, PdfWriter
import pytest

from app.core.pdf_edit import PdfEditError
from app.core.pdf_protection import protect_pdf, unprotect_pdf
from app.services.protection_service import ProtectionService
from tests.test_remove_pdf import make_pdf


@pytest.mark.parametrize("password", ["a", "senha com espaços", "ação-秘密"])
def test_aes_protection_and_authorized_removal(tmp_path: Path, password: str) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 3)
    before = source.read_bytes()
    protected = protect_pdf(source, tmp_path / "protegido.pdf", password, password)
    reader = PdfReader(protected)
    assert reader.is_encrypted
    assert reader.trailer["/Encrypt"]["/V"] == 5
    assert reader.trailer["/Encrypt"]["/R"] == 6
    assert reader.decrypt("errada") == 0
    assert reader.decrypt(password) != 0
    assert len(reader.pages) == 3
    unlocked = unprotect_pdf(protected, tmp_path / "desprotegido.pdf", password)
    final = PdfReader(unlocked)
    assert not final.is_encrypted
    for first, last in zip(PdfReader(source).pages, final.pages):
        assert first.get_contents().get_data() == last.get_contents().get_data()
        assert first.images[0].data == last.images[0].data
    assert source.read_bytes() == before
    if len(password) > 4:
        assert password.encode("utf-8") not in protected.read_bytes()
    assert not list(tmp_path.glob(".sigilopdf-*"))


@pytest.mark.parametrize("password,confirmation", [("", ""), ("abc", "abd"), ("é" * 64, "é" * 64)])
def test_invalid_new_password(tmp_path: Path, password: str, confirmation: str) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 1)
    with pytest.raises(PdfEditError):
        protect_pdf(source, tmp_path / "saida.pdf", password, confirmation)
    assert not (tmp_path / "saida.pdf").exists()


def test_wrong_password_and_no_bypass(tmp_path: Path) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 1)
    protected = protect_pdf(source, tmp_path / "protegido.pdf", "senha-correta", "senha-correta")
    with pytest.raises(PdfEditError, match="Senha incorreta") as error:
        unprotect_pdf(protected, tmp_path / "saida.pdf", "senha-incorreta")
    assert "senha-incorreta" not in str(error.value)
    assert not (tmp_path / "saida.pdf").exists()
    with pytest.raises(PdfEditError, match="não possui proteção"):
        unprotect_pdf(source, tmp_path / "saida.pdf", "qualquer")


def test_safe_output_and_secret_lifecycle(tmp_path: Path) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 1)
    with pytest.raises(PdfEditError, match="original"):
        protect_pdf(source, source, "senha", "senha")
    service = ProtectionService("senha", "senha")
    output = service.extract(str(source), str(tmp_path / "saida.pdf"), "", lambda *args: None)
    assert service.password == service.confirmation == ""
    result = protect_pdf(source, output, "nova", "nova")
    assert result.name == "saida_2.pdf"
    failure = ProtectionService("senha", "senha")
    with pytest.raises(PdfEditError):
        failure.extract(str(tmp_path / "ausente.pdf"), str(tmp_path / "erro.pdf"), "", lambda *args: None)
    assert failure.password == failure.confirmation == ""


def test_temporary_is_already_encrypted(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "original.pdf"
    make_pdf(source, 1)
    original_write = PdfWriter.write
    checked = []
    def check(writer, stream):
        result = original_write(writer, stream)
        stream.flush()
        staged = PdfReader(stream.name)
        assert staged.is_encrypted
        assert staged.decrypt("incorreta") == 0
        checked.append(True)
        return result
    monkeypatch.setattr(PdfWriter, "write", check)
    protect_pdf(source, tmp_path / "saida.pdf", "segredo-temporario", "segredo-temporario")
    assert checked == [True]
