from hashlib import sha256
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.core.pdf_info import PdfInfoError, read_pdf_info
from app.services.pdf_info_service import PdfInfoService


def create_pdf(path: Path, password: str | None = None) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.add_blank_page(width=200, height=300)
    writer.add_metadata({"/Title": "Documento de teste", "/Author": "Autoria", "/Subject": "Assunto", "/Creator": "Criador", "/Producer": "Produtor", "/CreationDate": "D:20260101120000-03'00'", "/ModDate": "D:20260102120000Z"})
    if password is not None:
        writer.encrypt(password)
    writer.write(path)


def test_info_and_original_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "informações.PDF"
    create_pdf(path)
    original = sha256(path.read_bytes()).digest()
    info = PdfInfoService().inspect(path)
    assert info.name == path.name
    assert info.path == str(path.resolve())
    assert info.size_bytes == path.stat().st_size
    assert info.page_count == 2
    assert info.version == "1.3"
    assert (info.title, info.author, info.subject) == ("Documento de teste", "Autoria", "Assunto")
    assert (info.creator, info.producer) == ("Criador", "Produtor")
    assert info.creation_date == "D:20260101120000-03'00'"
    assert info.modification_date == "D:20260102120000Z"
    assert not info.encrypted
    assert sha256(path.read_bytes()).digest() == original


@pytest.mark.parametrize("password,locked", [("segredo", True), ("", False)])
def test_encrypted(tmp_path: Path, password: str, locked: bool) -> None:
    path = tmp_path / "protegido.pdf"
    create_pdf(path, password)
    info = read_pdf_info(path)
    assert info.encrypted
    assert info.locked == locked
    assert info.page_count == (None if locked else 2)


def test_missing_metadata(tmp_path: Path) -> None:
    path = tmp_path / "simples.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(path)
    assert read_pdf_info(path).title == "Não informado"


@pytest.mark.parametrize("name,content,message", [
    ("ausente.pdf", None, "não foi encontrado"),
    ("texto.txt", b"texto", "extensão .pdf"),
    ("danificado.pdf", b"arquivo invalido", "Não foi possível ler"),
    ("vazio.pdf", b"", "Não foi possível ler"),
])
def test_friendly_errors(tmp_path: Path, name: str, content: bytes | None, message: str) -> None:
    path = tmp_path / name
    if content is not None:
        path.write_bytes(content)
    with pytest.raises(PdfInfoError, match=message):
        read_pdf_info(path)


def test_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def deny_open(*args: object, **kwargs: object) -> None:
        raise PermissionError("acesso negado")

    monkeypatch.setattr(Path, "open", deny_open)
    with pytest.raises(PdfInfoError, match="Sem permissão"):
        read_pdf_info(tmp_path / "privado.pdf")


def test_aes_encrypted(tmp_path: Path) -> None:
    path = tmp_path / "aes.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("senha", algorithm="AES-256")
    writer.write(path)
    info = read_pdf_info(path)
    assert info.encrypted and info.locked


def test_remote_path_rejected_before_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_resolution(*args: object, **kwargs: object) -> None:
        pytest.fail("Um caminho de rede não deve ser resolvido.")

    monkeypatch.setattr(Path, "resolve", forbid_resolution)
    with pytest.raises(PdfInfoError, match="compartilhamentos de rede"):
        read_pdf_info("//servidor/compartilhamento/documento.pdf")


def test_resolution_error_is_friendly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def deny_resolution(*args: object, **kwargs: object) -> None:
        raise PermissionError("acesso negado")

    monkeypatch.setattr(Path, "resolve", deny_resolution)
    with pytest.raises(PdfInfoError, match="Sem permissão"):
        read_pdf_info(tmp_path / "teste.pdf")


def test_invalid_file_does_not_log_content(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / "invalido.pdf"
    path.write_bytes(b"CONTEUDO_PRIVADO_DO_USUARIO")
    with pytest.raises(PdfInfoError):
        read_pdf_info(path)
    assert "CONTEUDO_PRIVADO" not in caplog.text
