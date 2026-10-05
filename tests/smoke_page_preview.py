"""Validação automatizada com janela nativa e PDF sintético de 100 páginas."""

import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox
from pytest import MonkeyPatch
from pypdf import PdfReader

from app.main import create_application
from app.ui.main_window import MainWindow
from tests.test_split_pdf import make_pdf


def main() -> None:
    application = create_application()
    assert application.platformName() == "windows"
    window = MainWindow()
    window.show()
    window.stack.setCurrentIndex(7)
    page = window.reorder_page
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()

    def wait(condition) -> None:
        deadline = time.monotonic() + 30
        while not condition() and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(0.002)
        assert condition()

    with TemporaryDirectory(prefix="sigilopdf-preview-") as folder:
        source = make_pdf(Path(folder) / "cem_paginas.pdf", 100)
        before = source.read_bytes()
        started = time.monotonic()
        page.inspect_file(str(source))
        updates = []
        page.worker.signals.thumbnail.connect(lambda index, data: updates.append(index))
        wait(lambda: page.worker is None)
        elapsed = time.monotonic() - started
        assert len(updates) == 100 and ticks
        page.pages.select_pages((1, 3))
        page.pages.move_selection_to(8)
        order = page.pages.order()
        page.preview.open_page(1)
        dialog = page.preview.dialog
        wait(lambda: not dialog.workers)
        assert not dialog.image.isNull()
        dialog.navigate(1)
        dialog.change_zoom(True)
        wait(lambda: not dialog.workers)
        dialog.fit()
        wait(lambda: not dialog.workers)
        dialog.close()
        page.pages.scrollToItem(page.pages.item(99))
        application.processEvents()
        output = Path(folder) / "resultado.pdf"
        page.save_to(str(output))
        wait(lambda: page.worker is None)
        assert [int(item.mediabox.width) for item in PdfReader(output).pages] == [101 + index for index in order]
        assert source.read_bytes() == before
        with MonkeyPatch.context() as patch:
            patch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
            page.restore_order()
        assert page.pages.order() == tuple(range(100))
        # Fechar imediatamente durante uma nova leitura não abandona workers.
        page.inspect_file(str(source))
        window.close()
        wait(lambda: not window.isVisible() and not window._has_pending_work())
    timer.stop()
    report = {"plataforma": application.platformName(), "paginas": 100,
              "miniaturas": len(updates), "segundos": round(elapsed, 3),
              "eventos_gui": len(ticks), "ordem_saida_validada": True,
              "original_preservado": True, "fechamento_sem_workers": True}
    destination = Path("build/validacao-preview.json")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
