"""Inicialização: python -m app.main."""

import sys
from importlib.resources import files

from PySide6.QtCore import QLibraryInfo, QLocale, QThreadPool, QTranslator
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.branding import brand_icon, configure_windows_identity
from app.version import __version__


def create_application() -> QApplication:
    QLocale.setDefault(QLocale("pt_BR"))
    # PyMuPDF não suporta chamadas concorrentes em threads do mesmo processo.
    # O pool executa tarefas em sequência; a thread gráfica permanece livre.
    QThreadPool.globalInstance().setMaxThreadCount(1)
    existing = QApplication.instance()
    if existing is not None:
        existing.setWindowIcon(brand_icon())
        return existing
    configure_windows_identity()
    application = QApplication(sys.argv)
    application.setApplicationName("SigiloPDF")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(brand_icon())
    translator = QTranslator(application)
    if translator.load("qtbase_pt_BR", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        application.installTranslator(translator)
        application._sigilopdf_translator = translator
    application.setStyleSheet(files("app.ui.styles").joinpath("main.qss").read_text(encoding="utf-8"))
    return application


def main() -> int:
    application = create_application()
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
