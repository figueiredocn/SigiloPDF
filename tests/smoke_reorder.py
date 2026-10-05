"""Validação da janela nativa, miniaturas, arraste e PDF final sintético."""

from pathlib import Path
from tempfile import TemporaryDirectory
from pytest import MonkeyPatch

from app.main import create_application
from tests.test_reorder_ui import test_organizer_flow


def main() -> None:
    with TemporaryDirectory(prefix="sigilopdf-organizar-") as folder, MonkeyPatch.context() as patch:
        test_organizer_flow(Path(folder), patch)
    print(f"Organizar páginas validado na plataforma {create_application().platformName()}.")


if __name__ == "__main__":
    main()
