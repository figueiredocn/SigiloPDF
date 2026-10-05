"""Autoteste explícito do executável distribuído; não lê documentos do usuário."""

from collections.abc import Callable
from io import BytesIO
import json
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import time

from PIL import Image
import pymupdf
from PySide6.QtWidgets import QApplication, QLabel
from pypdf import PdfReader

from app.main import create_application
from app.services.update_preferences import UpdatePreferenceStore, UpdatePreferences
from app.services.update_service import UpdateService, UpdateState
from app.ui.components.about_dialog import AboutDialog
from app.ui.main_window import MainWindow
from app.version import REPOSITORY_URL, __version__


def _wait(application: QApplication, ready: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 30
    while not ready() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert ready(), "Operação não concluída."


def _synthetic_pdf(path: Path) -> None:
    with pymupdf.open() as document:
        with Image.frombytes("RGB", (600, 800), Random(7).randbytes(1440000)) as image:
            data = BytesIO()
            image.save(data, "PNG")
        for index in range(3):
            page = document.new_page(width=200 + index, height=300)
            page.insert_image(page.rect, stream=data.getvalue())
            page.insert_text((20, 20), f"Pagina sintetica {index + 1}")
        document.save(path)


def _documents(window: MainWindow, folder: Path, application: QApplication) -> None:
    source = folder / "sintetico.pdf"
    _synthetic_pdf(source)
    original = source.read_bytes()
    window.info_page.inspect_file(str(source))
    _wait(application, lambda: window.info_page.worker is None)
    assert window.info_page.table.item(3, 1).text() == "3"
    merge = window.merge_page
    merge.add_files([str(source), str(source)])
    _wait(application, lambda: merge.worker is None)
    merged = folder / "juntos.pdf"
    merge.output.setText(str(merged))
    merge.merge_button.click()
    _wait(application, lambda: merge.worker is None)
    assert len(PdfReader(merged).pages) == 6
    reorder = window.reorder_page
    window.stack.setCurrentIndex(7)
    reorder.inspect_file(str(source))
    _wait(application, lambda: reorder.worker is None)
    assert all(not reorder.pages.item(index).icon().isNull() for index in range(3))
    reorder.pages.select_pages((2,))
    reorder.pages.move_selected(True)
    reorder.preview.open_page(2)
    dialog = reorder.preview.dialog
    _wait(application, lambda: not dialog.workers)
    assert not dialog.image.isNull()
    dialog.navigate(1)
    dialog.change_zoom(True)
    _wait(application, lambda: not dialog.workers)
    dialog.close()
    output = folder / "organizado.pdf"
    reorder.save_to(str(output))
    _wait(application, lambda: reorder.worker is None)
    assert [int(page.mediabox.width) for page in PdfReader(output).pages] == [202, 200, 201]
    assert source.read_bytes() == original


def _compression(window: MainWindow, folder: Path, application: QApplication) -> None:
    page = window.compression_page
    window.stack.setCurrentIndex(13)
    page.inspect_file(str(folder / "sintetico.pdf"))
    _wait(application, lambda: page.worker is None)
    page.compress_button.click()
    _wait(application, lambda: page.worker is None)
    assert page.result is not None
    assert page.result.compressed_size <= page.result.original_size
    output = folder / "comprimido.pdf"
    page.save_to(str(output))
    _wait(application, lambda: page.worker is None)
    assert len(PdfReader(output).pages) == 3


def _updates(window: MainWindow, folder: Path, application: QApplication) -> None:
    controller = window.updates
    controller.store = UpdatePreferenceStore(folder / "preferencias.json")
    controller.preferences = UpdatePreferences()
    data = {"tag_name": "v1.1.0", "name": "SigiloPDF 1.1.0", "draft": False,
            "prerelease": False, "html_url": f"{REPOSITORY_URL}/releases/tag/v1.1.0"}
    controller.service = UpdateService("1.0.0", lambda: data)
    controller.check_manual()
    _wait(application, lambda: controller.worker is None)
    assert controller.info.state == UpdateState.UPDATE_AVAILABLE
    controller.dialog.close()


def validate_build(report_path: str) -> int:
    application = create_application()
    window = MainWindow()
    window.updates.preferences.automatic = False
    window.show()
    result: dict[str, object] = {"versao": __version__, "plataforma": application.platformName(),
                                 "empacotado": bool(getattr(__import__("sys"), "frozen", False))}
    phase = "abertura"
    try:
        application.processEvents()
        assert window.isVisible() and window.windowHandle() is not None
        result[phase] = True
        with TemporaryDirectory(prefix="sigilopdf-validacao-") as temporary:
            folder = Path(temporary)
            phase = "informacoes_juncao_organizacao_preview_salvamento"
            _documents(window, folder, application)
            result[phase] = True
            phase = "compressao"
            _compression(window, folder, application)
            result[phase] = True
            phase = "sobre_e_interacao_oculta"
            about = AboutDialog(window)
            about.show()
            assert any(__version__ in label.text() for label in about.findChildren(QLabel))
            for _ in range(5):
                about.logo.click()
            assert about.special_dialog.isVisible()
            about.special_dialog.close()
            about.close()
            result[phase] = True
            phase = "atualizacoes_simuladas_sem_rede"
            _updates(window, folder, application)
            result[phase] = True
            window.close()
            _wait(application, lambda: not window.isVisible() and not window._has_pending_work())
            result["fechamento"] = True
        result["aprovado"] = True
    except Exception as error:
        result["aprovado"] = False
        result["fase_com_falha"] = phase
        result["erro"] = type(error).__name__
        window.close()
        _wait(application, lambda: not window._has_pending_work())
    with Path(report_path).open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    return 0 if result["aprovado"] else 1
