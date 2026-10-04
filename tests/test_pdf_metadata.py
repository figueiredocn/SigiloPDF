from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
import pytest

from app.core.pdf_metadata import edit_metadata, read_metadata
from app.core.pdf_protection import protect_pdf
from app.core.pdf_edit import PdfEditError
from tests.test_remove_pdf import make_pdf

XMP = b'''<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:pdf="http://ns.adobe.com/pdf/1.3/"><dc:title><rdf:Alt><rdf:li xml:lang="x-default">OrigemPrivadaUnica</rdf:li></rdf:Alt></dc:title><dc:creator><rdf:Seq><rdf:li>AutorPrivadoUnico</rdf:li></rdf:Seq></dc:creator><pdf:Keywords>chave privada</pdf:Keywords></rdf:Description></rdf:RDF></x:xmpmeta>'''


def source_pdf(path: Path, metadata: bool = True) -> Path:
    make_pdf(path, 3)
    reader = PdfReader(path)
    writer = PdfWriter(clone_from=reader)
    writer.add_attachment("anexo.txt", b"conteudo sintetico")
    writer.add_outline_item("Capitulo", 0)
    writer.metadata = None
    if metadata:
        writer.add_metadata({"/Title": "OrigemPrivadaUnica", "/Author": "AutorPrivadoUnico", "/Subject": "Teste", "/Keywords": "teste", "/Producer": "Produtor privado", "/Creator": "Criador privado", "/CreationDate": "D:20260101000000", "/ModDate": "D:20260102000000", "/CustomIdentity": "identidade privada"})
        writer.xmp_metadata = XMP
        writer.pages[0][NameObject("/Metadata")] = writer.root_object.raw_get("/Metadata")
    output = path.with_name("documento.pdf")
    writer.write(output)
    return output


def test_read_metadata(tmp_path: Path) -> None:
    source = source_pdf(tmp_path / "orig.pdf")
    snapshot = read_metadata(source)
    assert snapshot.fields == {"Título": "OrigemPrivadaUnica", "Autor": "AutorPrivadoUnico", "Assunto": "Teste", "Palavras-chave": "teste"}
    assert snapshot.info.page_count == 3
    assert snapshot.info.creator == "Criador privado"


@pytest.mark.parametrize("value", ["", "José — ação & <arquivo>", "Título acadêmico àéíõü", "漢字 e documentos"])
def test_edit_special_characters(tmp_path: Path, value: str) -> None:
    source = source_pdf(tmp_path / "orig.pdf")
    fields = {key: value for key in ("Título", "Autor", "Assunto", "Palavras-chave")}
    output = edit_metadata(source, tmp_path / "editado.pdf", fields)
    assert read_metadata(output).fields == fields
    reader = PdfReader(output)
    assert reader.xmp_metadata.dc_title["x-default"] == value
    assert reader.metadata.producer == "Produtor privado"
    assert reader.attachments["anexo.txt"] == [b"conteudo sintetico"]
    assert len(reader.outline) == 1
    for original, edited in zip(PdfReader(source).pages, reader.pages):
        assert edited.get_contents().get_data() == original.get_contents().get_data()


def test_remove_info_xmp_and_orphans(tmp_path: Path) -> None:
    source = source_pdf(tmp_path / "orig.pdf")
    before = source.read_bytes()
    result = edit_metadata(source, tmp_path / "sem.pdf", {}, clear=True)
    reader = PdfReader(result)
    assert reader.metadata is None
    assert reader.xmp_metadata is None
    assert "/Metadata" not in reader.pages[0]
    assert b"OrigemPrivadaUnica" not in result.read_bytes()
    assert b"AutorPrivadoUnico" not in result.read_bytes()
    assert len(reader.pages) == 3
    assert reader.attachments["anexo.txt"] == [b"conteudo sintetico"]
    assert source.read_bytes() == before


def test_without_metadata_and_safe_names(tmp_path: Path) -> None:
    source = source_pdf(tmp_path / "orig.pdf", False)
    assert all(value == "" for value in read_metadata(source).fields.values())
    result = edit_metadata(source, tmp_path / "saida.pdf", {"Autor": "Ana"})
    second = edit_metadata(source, result, {}, clear=True)
    assert second.name == "saida_2.pdf"
    assert read_metadata(result).fields["Autor"] == "Ana"


def test_xmp_fallback(tmp_path: Path) -> None:
    source = source_pdf(tmp_path / "orig.pdf", False)
    writer = PdfWriter(clone_from=PdfReader(source))
    writer.xmp_metadata = XMP
    writer.write(tmp_path / "xmp.pdf")
    assert read_metadata(tmp_path / "xmp.pdf").fields["Título"] == "OrigemPrivadaUnica"


def test_encrypted_technical_information(tmp_path: Path) -> None:
    source = source_pdf(tmp_path / "orig.pdf")
    protected = protect_pdf(source, tmp_path / "protegido.pdf", "senha", "senha")
    snapshot = read_metadata(protected)
    assert snapshot.info.encrypted
    assert snapshot.info.locked
    assert snapshot.info.page_count is None
    assert all(value == "" for value in snapshot.fields.values())
    with pytest.raises(PdfEditError, match="protegido por senha"):
        edit_metadata(protected, tmp_path / "saida.pdf", {}, clear=True)
