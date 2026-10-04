"""Reúne avisos das versões instaladas; não processa documentos de usuários."""

import json
import shutil
import sys
from importlib.metadata import distribution
from pathlib import Path

RUNTIME_PACKAGES = (
    "PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6",
    "pypdf", "PyMuPDF", "Pillow", "cryptography", "cffi", "pycparser", "PyInstaller",
)
ROOT = Path(__file__).resolve().parent.parent


def prepare_notices() -> None:
    destination = ROOT / "build" / "notices"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, destination / name)
    manifest: list[dict[str, str]] = []
    for name in RUNTIME_PACKAGES:
        package = distribution(name)
        manifest.append({"name": name, "version": package.version})
        copied = 0
        for item in package.files or ():
            if not any(word in str(item).lower() for word in ("license", "copying", "notice")):
                continue
            source = Path(package.locate_file(item))
            if not source.is_file():
                continue
            target = destination / name / str(item).replace("..", "_")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
        if not copied:
            raise RuntimeError(f"Nenhum aviso de licença encontrado para {name}.")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise RuntimeError("Licença do Python não encontrada.")
    shutil.copy2(python_license, destination / "PYTHON_LICENSE.txt")
    manifest.append({"name": "Python", "version": sys.version.split()[0]})
    (destination / "VERSOES.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    # O pacote editável contém direct_url.json com o caminho pessoal da máquina.
    # A versão precisa somente de METADATA, nunca desse arquivo de instalação.
    package = distribution("sigilopdf")
    metadata = ROOT / "build" / "metadata" / f"sigilopdf-{package.version}.dist-info"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "METADATA").write_text(package.read_text("METADATA"), encoding="utf-8")


if __name__ == "__main__":
    prepare_notices()
