"""Valida as operações finais na janela nativa com documentos sintéticos."""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.main import create_application
from tests.test_final_tools_ui import test_final_tools_flow, test_about_and_discreet_message


def main() -> None:
    with TemporaryDirectory(prefix="sigilopdf-final-") as folder:
        test_final_tools_flow(Path(folder))
        test_about_and_discreet_message()
    print(f"Numeração, metadados, proteção e Sobre validados; plataforma {create_application().platformName()}.")


if __name__ == "__main__":
    main()
