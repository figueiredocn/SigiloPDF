"""Validação da janela nativa, miniaturas, arraste e PDF final sintético."""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.main import create_application
from tests.test_reorder_ui import test_organizer_flow


def main() -> None:
    with TemporaryDirectory(prefix="sigilopdf-organizar-") as folder:
        test_organizer_flow(Path(folder))
    print(f"Organizar páginas validado na plataforma {create_application().platformName()}.")


if __name__ == "__main__":
    main()
