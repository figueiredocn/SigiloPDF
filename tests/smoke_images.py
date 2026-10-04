"""Fluxo nativo com imagens sintéticas e renderização da saída."""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.main import create_application
from tests.test_images_pdf_ui import test_images_flow


def main() -> None:
    with TemporaryDirectory(prefix="sigilopdf-imagens-") as folder:
        test_images_flow(Path(folder))
    print(f"Imagens para PDF validado; plataforma Qt: {create_application().platformName()}; originais preservados.")


if __name__ == "__main__":
    main()
