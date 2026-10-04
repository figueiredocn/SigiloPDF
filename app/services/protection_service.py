from collections.abc import Callable
from pathlib import Path

from app.core.pdf_edit import PdfEditError
from app.core.pdf_info import PdfInfo, PdfInfoError, read_pdf_info
from app.core.pdf_protection import protect_pdf, unprotect_pdf, validate_password
from app.services.extract_pdf_service import ExtractPdfService

__all__ = ["ProtectionService", "PdfEditError", "validate_password"]


class ProtectionService(ExtractPdfService):
    def __init__(self, password: str = "", confirmation: str = "", remove: bool = False) -> None:
        # Somente memória durante a operação; release_secrets elimina referências.
        self.password, self.confirmation, self.remove = password, confirmation, remove

    def inspect(self, path: str) -> PdfInfo:
        try:
            return read_pdf_info(path)
        except PdfInfoError as error:
            raise PdfEditError(str(error)) from error

    def release_secrets(self) -> None:
        self.password = self.confirmation = ""

    def extract(self, source: str, output: str, expression: str, progress: Callable[[int, str], None]) -> Path:
        try:
            progress(10, "Removendo a proteção com a senha informada…" if self.remove else "Protegendo o PDF com AES-256…")
            result = unprotect_pdf(source, output, self.password) if self.remove else protect_pdf(source, output, self.password, self.confirmation)
            progress(100, "Operação concluída.")
            return result
        finally:
            self.release_secrets()
