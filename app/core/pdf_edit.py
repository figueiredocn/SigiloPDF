"""Cópia completa e escrita segura compartilhada pelas operações finais."""

from collections.abc import Callable
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.core.extract_pdf import ExtractPdfError
from app.core.pdf_info import PdfInfoError, resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_pdf


class PdfEditError(ExtractPdfError):
    """Falha local de edição com mensagem amigável."""


def copy_and_edit(source: str | Path, output: str | Path,
                  edit: Callable[[PdfWriter], None], password: str | None = None, *, require_encrypted: bool = False) -> Path:
    created: list[CreatedFile] = []
    try:
        path, destination = resolve_local_path(source), resolve_local_path(output)
        if path.suffix.lower() != ".pdf" or destination.suffix.lower() != ".pdf":
            raise PdfEditError("Selecione arquivos com extensão .pdf.")
        if path == destination:
            raise PdfEditError("A saída não pode ser o arquivo original. Escolha outro nome.")
        if not destination.parent.is_dir():
            raise PdfEditError("A pasta de saída não existe. Escolha outra pasta.")
        with path.open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            if require_encrypted and not reader.is_encrypted:
                raise PdfEditError("Este PDF não possui proteção por senha para remover.")
            if reader.is_encrypted:
                if password is None:
                    raise PdfEditError("Este PDF está protegido por senha.")
                if not reader.decrypt(password):
                    raise PdfEditError("Senha incorreta. Confira a senha atual do PDF.")
            if not len(reader.pages):
                raise PdfEditError("O PDF precisa conter pelo menos uma página.")
            with PdfWriter() as writer:
                # __enter__ reinicializa o writer; clonar depois de entrar no contexto.
                writer.clone_document_from_reader(reader)
                writer.pdf_header = reader.pdf_header
                edit(writer)
                created.append(write_unique_pdf(writer, destination.parent, destination.stem))
        return created[0][0]
    except PdfEditError:
        remove_created(created)
        raise
    except PdfInfoError as error:
        remove_created(created)
        raise PdfEditError(str(error)) from error
    except Exception as error:
        remove_created(created)
        # Não anexar mensagens de bibliotecas: podem incluir conteúdo ou senhas.
        raise PdfEditError("Não foi possível salvar este PDF. Confira o arquivo, as permissões e o espaço disponível.") from error
    except BaseException:
        remove_created(created)
        raise
