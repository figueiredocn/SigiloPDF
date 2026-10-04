"""Validação manual automatizada da abertura com o plugin nativo do Qt."""

from PySide6.QtCore import QTimer

from app.main import create_application, main as run_application
from app.ui.main_window import MainWindow


def main() -> int:
    application = create_application()
    def verify() -> None:
        windows = [widget for widget in application.topLevelWidgets() if isinstance(widget, MainWindow)]
        opened = any(window.isVisible() and window.windowHandle() is not None for window in windows)
        print(f"Janela aberta: {opened}; plataforma Qt: {application.platformName()}")
        for window in windows:
            window.close()
        application.exit(0 if opened else 1)

    QTimer.singleShot(1500, verify)
    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
