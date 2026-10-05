"""Validação nativa com PDFs sintéticos de aproximadamente 5, 20 e 50 MB."""

import hashlib
from io import BytesIO
import json
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import time

from PIL import Image
from PySide6.QtCore import QTimer
import pymupdf

from app.main import create_application
from app.ui.main_window import MainWindow


def fixture(path: Path, pages: int) -> None:
    with pymupdf.open() as document:
        for index in range(pages):
            with Image.frombytes("RGB", (1100, 1600), Random(index).randbytes(5280000)) as image:
                stream = BytesIO()
                image.save(stream, "PNG")
                page = document.new_page()
                page.insert_image(page.rect, stream=stream.getvalue())
                page.insert_text((30, 40), f"Documento sintetico - pagina {index + 1}")
        document.save(path)


def wait(page, application) -> None:
    limit = time.monotonic() + 180
    while page.worker is not None and time.monotonic() < limit:
        application.processEvents()
        time.sleep(0.005)
    if page.worker is not None:
        raise RuntimeError("A operação excedeu o limite do teste.")


def main() -> int:
    reports = []
    with TemporaryDirectory(prefix="sigilopdf-teste-compressao-") as temporary:
        folder = Path(temporary)
        files = []
        for pages in (1, 4, 10):
            source = folder / f"sintetico_{pages}.pdf"
            fixture(source, pages)
            files.append(source)
        application = create_application()
        window = MainWindow()
        window.show()
        window.stack.setCurrentIndex(13)
        page = window.compression_page
        ticks: list[float] = []
        timer = QTimer()
        timer.setInterval(20)
        timer.timeout.connect(lambda: ticks.append(time.monotonic()))
        timer.start()
        try:
            for source in files:
                before = hashlib.sha256(source.read_bytes()).hexdigest()
                page.inspect_file(str(source))
                wait(page, application)
                assert page.info is not None, page.status.text()
                ticks.clear()
                started = time.monotonic()
                page.compress_button.click()
                wait(page, application)
                elapsed = time.monotonic() - started
                assert page.result is not None, page.status.text()
                result = page.result
                assert result.significant
                assert result.compressed_size < result.original_size
                assert len(ticks) > 2
                assert window.isVisible() and application.platformName() == "windows"
                output = folder / "resultado.pdf"
                page.save_to(str(output))
                wait(page, application)
                with pymupdf.open(page.result.output_path) as document:
                    assert len(document) == page.info.page_count
                    assert "Documento sintetico" in document[0].get_text()
                    assert document[0].get_pixmap().width > 0
                assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                preview_folder = result.output_path.parent
                reports.append({"original_bytes": result.original_size,
                                "final_bytes": result.compressed_size,
                                "reducao_percentual": round(result.reduction_percent, 2),
                                "segundos": round(elapsed, 2), "eventos_ui": len(ticks),
                                "maior_intervalo_ui_segundos": round(max(b-a for a,b in zip(ticks,ticks[1:])), 3),
                                "original_preservado": True})
                page.clear_result()
                assert not preview_folder.exists()
                print(json.dumps(reports[-1], ensure_ascii=False), flush=True)
        finally:
            timer.stop()
            window.close()
            application.processEvents()
    report = {"plataforma": "windows", "janela_aberta": True,
              "temporarios_limpos": True, "casos": reports}
    Path("build").mkdir(exist_ok=True)
    Path("build/validacao-compressao.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
