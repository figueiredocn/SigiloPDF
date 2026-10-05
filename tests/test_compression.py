from io import BytesIO
from pathlib import Path
from random import Random
from threading import Event

from PIL import Image
import pymupdf
import pytest

from app.core.compression.compressor import compress_pdf
from app.core.compression.models import (CompressionError, CompressionMode,
                                         CompressionOptions, MAX_ATTEMPTS, PasswordRequired)
from app.core.compression.pdf_optimizer import inspect_pdf
from app.core.compression.sizes import format_size, parse_target_size
from app.services.compression_service import CompressionService


def make_pdf(path: Path, images: bool = False, pages: int = 1, password: str = "") -> Path:
    with pymupdf.open() as document:
        for index in range(pages):
            page = document.new_page()
            if images:
                with Image.frombytes("RGB", (1000, 1400), Random(index).randbytes(1000 * 1400 * 3)) as image:
                    buffer = BytesIO()
                    image.save(buffer, "PNG")
                    page.insert_image(page.rect, stream=buffer.getvalue())
            page.insert_text((50, 50), f"Texto selecionavel {index + 1}")
        document.set_metadata({"title": "Documento sintético", "author": "Teste local", "creationDate": "D:20260101000000"})
        kwargs = dict(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password) if password else {}
        document.save(path, **kwargs)
    return path


@pytest.mark.parametrize("mode", list(CompressionMode))
def test_modes_preserve_original_and_readable_pages(tmp_path: Path, mode: CompressionMode) -> None:
    source = make_pdf(tmp_path / "original.pdf", images=True, pages=2)
    before = source.read_bytes()
    preview = compress_pdf(source, CompressionOptions(mode, 500 * 1024 if mode == CompressionMode.TARGET else None))
    folder = preview.result.output_path.parent
    try:
        result = preview.result
        assert result.compressed_size == result.output_path.stat().st_size
        assert result.compressed_size <= result.original_size
        assert result.significant
        assert result.reduction_bytes == result.original_size - result.compressed_size
        assert 1 <= result.attempts <= MAX_ATTEMPTS
        with pymupdf.open(result.output_path) as document:
            assert document.page_count == 2
            assert document.metadata["title"] == "Documento sintético"
            assert document.metadata["author"] == "Teste local"
            assert document.metadata["creationDate"] == "D:20260101000000"
            for page in document:
                assert "Texto selecionavel" in page.get_text()
                assert page.get_pixmap().width > 0
        assert source.read_bytes() == before
    finally:
        preview.close()
    assert not folder.exists()


@pytest.mark.parametrize("pages", [1, 20])
def test_text_only_and_small_pdf(tmp_path: Path, pages: int) -> None:
    source = make_pdf(tmp_path / "texto.pdf", pages=pages)
    preview = compress_pdf(source)
    try:
        assert preview.result.compressed_size <= source.stat().st_size
        with pymupdf.open(preview.result.output_path) as document:
            assert len(document) == pages
            assert "Texto selecionavel 1" in document[0].get_text()
    finally:
        preview.close()


def test_target_reached_without_unnecessary_loss(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "texto.pdf")
    preview = compress_pdf(source, CompressionOptions(CompressionMode.TARGET, 50 * 1024))
    try:
        assert preview.result.target_reached
        assert preview.result.attempts == 1
    finally:
        preview.close()


def test_impossible_target_keeps_best_and_limits_attempts(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "grande.pdf", images=True, pages=3)
    preview = compress_pdf(source, CompressionOptions(CompressionMode.TARGET, 50 * 1024))
    try:
        assert not preview.result.target_reached
        assert preview.result.attempts == MAX_ATTEMPTS
        assert preview.result.compressed_size < source.stat().st_size
        assert any("Não foi possível atingir" in warning for warning in preview.result.warnings)
        assert list(preview.result.output_path.parent.iterdir()) == [preview.result.output_path]
    finally:
        preview.close()


def test_image_target_is_reached_and_stops_early(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "imagem.pdf", images=True)
    target = 2 * 1024 ** 2
    preview = compress_pdf(source, CompressionOptions(CompressionMode.TARGET, target))
    try:
        assert preview.result.target_reached
        assert preview.result.compressed_size <= target
        assert 1 < preview.result.attempts < MAX_ATTEMPTS
    finally:
        preview.close()


def test_network_temporary_folder_is_rejected_before_creation(tmp_path: Path, monkeypatch) -> None:
    import app.core.compression.compressor as module
    source = make_pdf(tmp_path / "local.pdf")
    monkeypatch.setattr(module, "gettempdir", lambda: "//servidor/pasta")
    created = []
    monkeypatch.setattr(module, "TemporaryDirectory", lambda **kwargs: created.append(kwargs))
    with pytest.raises(CompressionError):
        compress_pdf(source)
    assert not created


def test_already_optimized_pdf_never_returns_larger_output(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "texto.pdf")
    first = compress_pdf(source)
    second = compress_pdf(first.result.output_path)
    try:
        assert second.result.compressed_size <= first.result.compressed_size
        assert not second.result.significant
        assert any("bem otimizado" in text for text in second.result.warnings)
    finally:
        second.close()
        first.close()


def test_form_links_outlines_annotations_xmp_and_attachment_survive(tmp_path: Path) -> None:
    source = tmp_path / "formulario.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), "Texto vetorial")
        with Image.frombytes("RGB", (500, 500), Random(1).randbytes(750000)) as image:
            buffer = BytesIO()
            image.save(buffer, "PNG")
            page.insert_image(pymupdf.Rect(50, 300, 300, 550), stream=buffer.getvalue())
        page.draw_rect(pymupdf.Rect(40, 40, 200, 60))
        widget = pymupdf.Widget()
        widget.field_name, widget.field_value = "nome", "Teste local"
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.rect = pymupdf.Rect(50, 80, 250, 110)
        page.add_widget(widget)
        page.add_text_annot((30, 150), "Anotação sintética")
        page.insert_link({"kind": pymupdf.LINK_GOTO, "from": pymupdf.Rect(40, 200, 180, 220), "page": 0})
        document.set_toc([[1, "Início", 1]])
        document.set_xml_metadata('<x:xmpmeta xmlns:x="adobe:ns:meta/"><dado>Teste</dado></x:xmpmeta>')
        document.embfile_add("teste.txt", b"Conteudo sintetico")
        document.save(source)
    preview = compress_pdf(source)
    try:
        assert preview.result.significant
        with pymupdf.open(preview.result.output_path) as document:
            assert document.get_toc() == [[1, "Início", 1]]
            assert "Teste" in document.get_xml_metadata()
            assert document.embfile_get("teste.txt") == b"Conteudo sintetico"
            page = document[0]
            assert list(page.widgets())[0].field_value == "Teste local"
            assert len(list(page.annots())) == 1
            assert len(page.get_links()) == 1
            assert page.get_drawings()
    finally:
        preview.close()


def test_password_is_required_and_encryption_is_preserved(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "protegido.pdf", images=True, password="segredo-local")
    before = source.read_bytes()
    with pytest.raises(PasswordRequired):
        compress_pdf(source)
    with pytest.raises(CompressionError, match="Senha incorreta"):
        compress_pdf(source, password="errada")
    assert inspect_pdf(source, "segredo-local").encrypted
    preview = compress_pdf(source, password="segredo-local")
    try:
        with pymupdf.open(preview.result.output_path) as document:
            assert document.needs_pass
            assert document.authenticate("segredo-local")
            assert "Texto selecionavel" in document[0].get_text()
        assert source.read_bytes() == before
    finally:
        preview.close()


def test_signature_requires_confirmation(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "assinatura.pdf")
    with pymupdf.open(source) as document:
        document.xref_set_key(document.pdf_catalog(), "AcroForm", "<</SigFlags 3>>")
        document.save(tmp_path / "assinado.pdf")
    assert inspect_pdf(tmp_path / "assinado.pdf").signed
    with pytest.raises(CompressionError, match="Confirme"):
        compress_pdf(tmp_path / "assinado.pdf")
    preview = compress_pdf(tmp_path / "assinado.pdf", allow_signed=True)
    preview.close()


def test_empty_user_password_keeps_encryption_without_prompt(tmp_path: Path) -> None:
    source = tmp_path / "senha_vazia.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.save(source, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="dono", user_pw="")
    info = inspect_pdf(source)
    assert info.encrypted and not info.needs_password
    preview = compress_pdf(source)
    try:
        with pymupdf.open(preview.result.output_path) as document:
            assert document.metadata["encryption"] is not None
    finally:
        preview.close()


def test_cleanup_permission_failure_is_reported_without_raw_exception(tmp_path: Path, monkeypatch) -> None:
    source = make_pdf(tmp_path / "original.pdf")
    service = CompressionService()
    service.compress(str(source), CompressionOptions(), None, False, lambda *_: None, lambda: False)
    temporary = service.preview.temporary
    cleanup = temporary.cleanup
    def denied() -> None:
        raise PermissionError("mensagem interna")
    monkeypatch.setattr(temporary, "cleanup", denied)
    try:
        assert not service.release_preview()
        assert service.preview is None
    finally:
        cleanup()


def test_save_conflicts_and_original_are_protected(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "relatorio.pdf", images=True)
    before = source.read_bytes()
    service = CompressionService()
    result = service.compress(str(source), CompressionOptions(), None, False, lambda *_: None, lambda: False)
    folder = result.output_path.parent
    try:
        with pytest.raises(CompressionError, match="original"):
            service.save(str(source), lambda *_: None, lambda: False)
        output = tmp_path / "relatorio_comprimido.pdf"
        output.write_bytes(b"existente")
        saved = service.save(str(output), lambda *_: None, lambda: False)
        assert saved.output_path.name == "relatorio_comprimido_2.pdf"
        assert output.read_bytes() == b"existente"
        assert saved.output_path.stat().st_size == result.compressed_size
        assert not list(tmp_path.glob(".sigilopdf-*.tmp"))
        assert source.read_bytes() == before
    finally:
        service.release_preview()
    assert not folder.exists()


@pytest.mark.parametrize("failure", ["cancel", "error"])
def test_temporary_cleanup_on_failure(tmp_path: Path, monkeypatch, failure: str) -> None:
    import app.core.compression.compressor as module
    from tempfile import TemporaryDirectory
    source = make_pdf(tmp_path / "original.pdf", images=True)
    folders: list[Path] = []
    def temporary(**kwargs):
        kwargs["dir"] = tmp_path
        directory = TemporaryDirectory(**kwargs)
        folders.append(Path(directory.name))
        return directory
    monkeypatch.setattr(module, "TemporaryDirectory", temporary)
    event = Event()
    def progress(value: int, text: str) -> None:
        if "Tentativa" in text:
            event.set()
    if failure == "error":
        def fail(*args, **kwargs):
            raise OSError("Erro sintético")
        monkeypatch.setattr(module, "save_optimized", fail)
    with pytest.raises(CompressionError):
        compress_pdf(source, progress=progress if failure == "cancel" else lambda *_: None, cancelled=event.is_set)
    assert folders and all(not path.exists() for path in folders)


@pytest.mark.parametrize("text,unit", [("0", "MB"), ("-5", "MB"), ("abc", "KB"), ("NaN", "MB"), ("Infinity", "MB"), ("49", "KB"), ("11", "GB"), ("10241", "MB")])
def test_invalid_target_sizes(text: str, unit: str) -> None:
    with pytest.raises(CompressionError, match="50 KB"):
        parse_target_size(text, unit)


def test_size_conversion_and_portuguese_format() -> None:
    assert parse_target_size("2,5", "MB") == 2621440
    assert parse_target_size("500", "KB") == 512000
    assert format_size(13842391) == "13,20 MB"
    assert format_size(1) == "1,00 B"
    assert format_size(1024 ** 3) == "1,00 GB"


@pytest.mark.parametrize("name", ["ausente.pdf", "invalido.pdf", "imagem.png"])
def test_invalid_file_has_friendly_error(tmp_path: Path, name: str) -> None:
    if name != "ausente.pdf":
        (tmp_path / name).write_bytes(b"arquivo invalido")
    with pytest.raises(CompressionError):
        compress_pdf(tmp_path / name)
