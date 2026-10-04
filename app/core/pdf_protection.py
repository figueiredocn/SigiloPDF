"""Proteção AES-256 e remoção mediante senha fornecida, sem persistência."""

from pathlib import Path

from pypdf import PdfWriter

from app.core.pdf_edit import PdfEditError, copy_and_edit


def validate_password(password: str, confirmation: str | None = None) -> None:
    if not isinstance(password, str) or not password:
        raise PdfEditError("Informe uma senha. A senha não pode estar vazia.")
    if confirmation is not None and password != confirmation:
        raise PdfEditError("A senha e a confirmação não coincidem.")
    # AES-256 aceita até 127 bytes UTF-8; recusar truncamento silencioso.
    if len(password.encode("utf-8")) > 127:
        raise PdfEditError("A senha excede o limite de 127 bytes UTF-8 da criptografia PDF.")


def protect_pdf(source: str | Path, output: str | Path, password: str, confirmation: str) -> Path:
    if confirmation is None:
        raise PdfEditError("A senha e a confirmação não coincidem.")
    validate_password(password, confirmation)
    def edit(writer: PdfWriter) -> None:
        writer.pdf_header = "%PDF-2.0"
        writer.encrypt(password, algorithm="AES-256")
    return copy_and_edit(source, output, edit)


def unprotect_pdf(source: str | Path, output: str | Path, password: str) -> Path:
    validate_password(password)
    def edit(writer: PdfWriter) -> None:
        # O leitor já validou a senha; o clone completo não carrega /Encrypt.
        pass
    return copy_and_edit(source, output, edit, password=password, require_encrypted=True)
