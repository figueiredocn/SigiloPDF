"""Valida os quatro modos na janela real com um PDF sintético temporário."""

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QMimeData, QPointF, QTimer, Qt, QUrl
from PySide6.QtGui import QDropEvent
from pypdf import PdfReader, PdfWriter

from app.main import create_application, main as run_application
from app.services.split_pdf_service import SplitMode
from app.ui.main_window import MainWindow


def main() -> int:
    application = create_application()
    with TemporaryDirectory(prefix="sigilopdf-divisao-") as directory:
        folder = Path(directory)
        source = folder / "documento.pdf"
        writer = PdfWriter()
        for number in range(1, 11):
            writer.add_blank_page(width=100 + number, height=300)
        writer.write(source)
        original = source.read_bytes()
        cases = [
            (SplitMode.EACH_PAGE, "", [[100 + n] for n in range(1, 11)]),
            (SplitMode.RANGE, "1-5", [[101, 102, 103, 104, 105]]),
            (SplitMode.SPECIFIC, "1,3,5", [[101, 103, 105]]),
            (SplitMode.COMBINATION, "1-3,5,8-10", [[101, 102, 103, 105, 108, 109, 110]]),
        ]
        stage, case_index = 0, 0
        timer = QTimer(application)
        timer.setInterval(20)

        def poll() -> None:
            nonlocal stage, case_index
            try:
                window = next(w for w in application.topLevelWidgets() if isinstance(w, MainWindow))
                page = window.split_page
                if stage == 0:
                    assert window.isVisible()
                    window.stack.setCurrentIndex(3)
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(str(source))])
                    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    page.drop_area.dropEvent(event)
                    stage = 1
                elif stage == 1 and page.worker is None:
                    assert page.info is not None
                    mode, expression, expected = cases[case_index]
                    page.mode.setCurrentIndex(page.mode.findData(mode))
                    page.expression.setText(expression)
                    page.folder.setText(str(folder))
                    page.split_button.click()
                    stage = 2
                elif stage == 2 and page.worker is None:
                    assert page.progress.value() == 100
                    paths = page.results.toPlainText().splitlines()
                    actual: list[list[int]] = []
                    for path in paths:
                        with Path(path).open("rb") as stream:
                            actual.append([int(p.mediabox.width) for p in PdfReader(stream).pages])
                    assert actual == cases[case_index][2]
                    assert source.read_bytes() == original
                    case_index += 1
                    if case_index < len(cases):
                        stage = 1
                    else:
                        print(f"Divisão validada nos quatro modos; plataforma Qt: {application.platformName()}; original preservado.")
                        timer.stop()
                        window.close()
                        application.exit(0)
            except Exception as error:
                print(f"Falha na validação da divisão: {error}")
                timer.stop()
                application.exit(1)

        timer.timeout.connect(poll)
        timer.start()
        QTimer.singleShot(15000, lambda: application.exit(1))
        return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
