"""Geração de PDF com imagens originais e posicionamento proporcional."""

from collections.abc import Callable, Sequence
from pathlib import Path
import zlib

from PIL import ImageOps
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject, StreamObject

from app.core.image_reader import ImagesPdfError, open_image, white_background
from app.core.pdf_info import resolve_local_path
from app.core.split_output import CreatedFile, remove_created, write_unique_pdf

PAGE_SIZES = {"A4": (595.276, 841.89), "A3": (841.89, 1190.551), "Carta": (612.0, 792.0)}
MARGINS = {"Sem margem": 0, "Pequena": 12, "Média": 24, "Grande": 36}
ORIENTATIONS = ("Automática", "Retrato", "Paisagem")
FIT_MODES = ("Ajustar à página", "Preencher página", "Tamanho original")
IMAGE_SIZE = "Ajustar ao tamanho da imagem"


def page_geometry(width: int, height: int, dpi: tuple[float, float], page_size: str,
                  orientation: str, fit_mode: str, margin: str) -> tuple[float, ...]:
    if page_size not in (*PAGE_SIZES, IMAGE_SIZE) or orientation not in ORIENTATIONS or fit_mode not in FIT_MODES or margin not in MARGINS:
        raise ImagesPdfError("Confira as configurações de página, orientação, ajuste e margem.")
    border = MARGINS[margin]
    iw, ih = width * 72 / dpi[0], height * 72 / dpi[1]
    pw, ph = (iw + 2 * border, ih + 2 * border) if page_size == IMAGE_SIZE else PAGE_SIZES[page_size]
    landscape = orientation == "Paisagem" or (orientation == "Automática" and width > height)
    pw, ph = (max(pw, ph), min(pw, ph)) if landscape else (min(pw, ph), max(pw, ph))
    if max(pw, ph) > 14400 or min(pw, ph) <= 2 * border:
        raise ImagesPdfError("As dimensões da página excedem os limites suportados. Escolha A4, A3 ou Carta.")
    available_w, available_h = pw - 2 * border, ph - 2 * border
    factor = 1.0 if fit_mode == "Tamanho original" else (min if fit_mode == "Ajustar à página" else max)(available_w / iw, available_h / ih)
    draw_w, draw_h = iw * factor, ih * factor
    return pw, ph, draw_w, draw_h, (pw - draw_w) / 2, (ph - draw_h) / 2, border


def _add_image(writer: PdfWriter, source: Path, page_size: str, orientation: str, fit_mode: str, margin: str) -> None:
    with open_image(source) as original:
        dpi_value = original.info.get("dpi", (96, 96))
        try:
            dpi = tuple(float(value) if 1 <= float(value) <= 9600 else 96.0 for value in dpi_value[:2])
            if len(dpi) != 2:
                dpi = (96.0, 96.0)
        except (TypeError, ValueError):
            dpi = (96.0, 96.0)
        rotated = original.getexif().get(274, 1) in (5, 6, 7, 8)
        preserve_jpeg = original.format == "JPEG" and original.mode in ("RGB", "L") and original.getexif().get(274, 1) == 1
        normalized = original if preserve_jpeg else white_background(ImageOps.exif_transpose(original))
        if rotated:
            dpi = dpi[::-1]
        geometry = page_geometry(*normalized.size, dpi, page_size, orientation, fit_mode, margin)
        stream = StreamObject()
        stream._data = source.read_bytes() if preserve_jpeg else zlib.compress(normalized.tobytes())
        stream.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                       NameObject("/Width"): NumberObject(normalized.width), NameObject("/Height"): NumberObject(normalized.height),
                       NameObject("/ColorSpace"): NameObject("/DeviceGray" if normalized.mode == "L" else "/DeviceRGB"),
                       NameObject("/BitsPerComponent"): NumberObject(8), NameObject("/Filter"): NameObject("/DCTDecode" if preserve_jpeg else "/FlateDecode")})
        pw, ph, dw, dh, x, y, border = geometry
        page = writer.add_blank_page(width=pw, height=ph)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Imagem"): writer._add_object(stream)})})
        content = DecodedStreamObject()
        content.set_data(f"q {border} {border} {pw-2*border} {ph-2*border} re W n {dw} 0 0 {dh} {x} {y} cm /Imagem Do Q".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)


def images_to_pdf(image_paths: Sequence[str | Path], output_path: str | Path, page_size: str = "A4",
                  orientation: str = "Automática", fit_mode: str = "Ajustar à página", margin: str = "Pequena",
                  progress: Callable[[int, str], None] | None = None) -> Path:
    created: list[CreatedFile] = []
    report = progress or (lambda value, text: None)
    try:
        if not image_paths:
            raise ImagesPdfError("Adicione pelo menos uma imagem para gerar o PDF.")
        sources = [resolve_local_path(path) for path in image_paths]
        output = resolve_local_path(output_path)
        if output in sources:
            raise ImagesPdfError("A saída não pode substituir uma imagem original.")
        if output.suffix.lower() != ".pdf" or not output.parent.is_dir():
            raise ImagesPdfError("Escolha um arquivo .pdf em uma pasta existente.")
        with PdfWriter() as writer:
            for index, source in enumerate(sources):
                report(int(90 * index / len(sources)), f"Convertendo imagem {index + 1} de {len(sources)}…")
                _add_image(writer, source, page_size, orientation, fit_mode, margin)
            report(95, "Salvando o PDF…")
            created.append(write_unique_pdf(writer, output.parent, output.stem))
        report(100, "Conversão concluída.")
        return created[0][0]
    except ImagesPdfError:
        remove_created(created)
        raise
    except Exception as error:
        remove_created(created)
        raise ImagesPdfError("Não foi possível gerar o PDF. Confira as imagens, as permissões e o espaço disponível.") from error
    except BaseException:
        remove_created(created)
        raise
