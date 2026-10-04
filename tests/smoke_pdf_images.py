"""Exportação em janela nativa e responsividade com 50 páginas sintéticas."""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.main import create_application
from tests.test_pdf_images_ui import test_export_flow, test_fifty_pages_responsive


def main() -> None:
    with TemporaryDirectory(prefix="sigilopdf-exportar-") as folder:
        flow, large = Path(folder) / "fluxo", Path(folder) / "grande"
        flow.mkdir()
        large.mkdir()
        test_export_flow(flow)
        test_fifty_pages_responsive(large)
    print(f"PDF para imagens validado: PNG/JPEG, seleção, 50 páginas; plataforma {create_application().platformName()}.")


if __name__ == "__main__":
    main()
