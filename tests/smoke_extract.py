"""Valida Informações do PDF e Extrair páginas na janela real."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QMimeData, QPointF, QTimer, Qt, QUrl
from PySide6.QtGui import QDropEvent
from pypdf import PdfReader, PdfWriter

from app.main import create_application, main as run_application
from app.ui.main_window import MainWindow


def main() -> int:
    application = create_application()
    with TemporaryDirectory(prefix="sigilopdf-extracao-") as directory:
        folder = Path(directory)
        source = folder / "relatorio.pdf"
        writer = PdfWriter()
        for number in range(1, 9):
            writer.add_blank_page(width=100 + number, height=300)
        writer.write(source)
        original = source.read_bytes()
        stage = 0
        timer = QTimer(application)
        timer.setInterval(20)

        def poll() -> None:
            nonlocal stage
            try:
                window = next(w for w in application.topLevelWidgets() if isinstance(w, MainWindow))
                page = window.extract_page
                if stage == 0:
                    assert window.isVisible()
                    window.stack.setCurrentIndex(1)
                    window.info_page.inspect_file(str(source))
                    stage = 1
                elif stage == 1 and window.info_page.worker is None:
                    assert window.info_page.table.rowCount() == 13
                    assert window.info_page.table.item(3, 1).text() == "8"
                    window.stack.setCurrentIndex(4)
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(str(source))])
                    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    page.drop_area.dropEvent(event)
                    stage = 2
                elif stage == 2 and page.worker is None:
                    assert page.info is not None
                    page.expression.setText("8,2-4,2")
                    assert "8, 2, 3, 4" in page.summary.toPlainText()
                    assert not (folder / "relatorio_extraido.pdf").exists()
                    page.extract_button.click()
                    stage = 3
                elif stage == 3 and page.worker is None:
                    assert page.progress.value() == 100
                    with (folder / "relatorio_extraido.pdf").open("rb") as stream:
                        assert [int(p.mediabox.width) - 100 for p in PdfReader(stream).pages] == [8, 2, 3, 4]
                    assert source.read_bytes() == original
                    print(f"Informações do PDF e extração validadas; plataforma Qt: {application.platformName()}; original preservado.")
                    timer.stop()
                    window.close()
                    application.exit(0)
            except Exception as error:
                print(f"Falha na validação da extração: {error}")
                timer.stop()
                application.exit(1)

        timer.timeout.connect(poll)
        timer.start()
        QTimer.singleShot(15000, lambda: application.exit(1))
        return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
