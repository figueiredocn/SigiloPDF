"""Validação da junção usando a janela real e PDFs sintéticos temporários."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QMimeData, QPointF, QTimer, Qt, QUrl
from PySide6.QtGui import QDropEvent
from pypdf import PdfReader, PdfWriter

from app.main import create_application, main as run_application
from app.ui.main_window import MainWindow


def main() -> int:
    application = create_application()
    with TemporaryDirectory(prefix="sigilopdf-validacao-") as folder:
        root = Path(folder)
        paths = [root / "primeiro.pdf", root / "segundo.pdf"]
        for index, path in enumerate(paths):
            writer = PdfWriter()
            writer.add_blank_page(width=100 + index, height=300)
            writer.write(path)
        originals = [path.read_bytes() for path in paths]
        stage = 0
        timer = QTimer(application)
        timer.setInterval(20)

        def poll() -> None:
            nonlocal stage
            try:
                window = next(widget for widget in application.topLevelWidgets() if isinstance(widget, MainWindow))
                page = window.merge_page
                if stage == 0:
                    assert window.isVisible()
                    window.stack.setCurrentIndex(2)
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
                    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    page.drop_area.dropEvent(event)
                    stage = 1
                elif stage == 1 and page.worker is None:
                    assert page.files.count() == 2
                    page.files.setCurrentRow(1)
                    page.up_button.click()
                    page.output.setText(str(root / "resultado.pdf"))
                    page.merge_button.click()
                    stage = 2
                elif stage == 2 and page.worker is None:
                    assert page.progress.value() == 100
                    assert "sucesso" in page.status.text()
                    with (root / "resultado.pdf").open("rb") as stream:
                        assert [float(p.mediabox.width) for p in PdfReader(stream).pages] == [101, 100]
                    assert originals == [path.read_bytes() for path in paths]
                    print(f"Junção validada na janela real; plataforma Qt: {application.platformName()}; originais preservados.")
                    timer.stop()
                    window.close()
                    application.exit(0)
            except Exception as error:
                print(f"Falha na validação da junção: {error}")
                timer.stop()
                application.exit(1)

        timer.timeout.connect(poll)
        timer.start()
        QTimer.singleShot(15000, lambda: application.exit(1))
        return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
