"""Reúne avisos das versões instaladas; não processa documentos de usuários."""

import json
import shutil
import sys
import runpy
import tarfile
from importlib.metadata import distribution
from pathlib import Path, PurePosixPath

RUNTIME_PACKAGES = (
    "PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6",
    "pypdf", "PyMuPDF", "Pillow", "cryptography", "cffi", "pycparser", "PyInstaller",
)
ROOT = Path(__file__).resolve().parent.parent
RELEASE = runpy.run_path(str(ROOT / "app" / "version.py"))["__version__"]


def copy_source_notices(destination: Path) -> None:
    folder = ROOT / "build" / "corresponding-sources"
    for name in ("SOURCE_LOCK.json", "VENDOR_SOURCE_LOCK.json", "EXTRA_SOURCE_LOCK.json"):
        records = json.loads((folder / name).read_text(encoding="utf-8"))
        for record in records:
            with tarfile.open(folder / record["filename"]) as archive:
                for item in archive.getmembers():
                    basename = Path(item.name).name.upper()
                    if not item.isfile() or item.size > 512 * 1024:
                        continue
                    if not (basename.startswith(("LICENSE", "COPYING", "NOTICE", "COPYRIGHT", "OFL")) or "/LICENSES/" in item.name.upper()):
                        continue
                    # Ler os avisos sem extrair caminhos fornecidos pelo arquivo.
                    relative = PurePosixPath(item.name)
                    if relative.is_absolute() or ".." in relative.parts or any(":" in part for part in relative.parts):
                        raise RuntimeError("Caminho inválido em arquivo de fontes.")
                    target = destination / "fontes" / record["component"] / Path(*relative.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(item).read())
    for name in ("SOURCE_LOCK.json", "VENDOR_SOURCE_LOCK.json", "EXTRA_SOURCE_LOCK.json"):
        shutil.copy2(folder / name, destination / name)


def prepare_notices() -> None:
    destination = ROOT / "build" / "notices"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "DISTRIBUTION_LICENSE.md"):
        shutil.copy2(ROOT / name, destination / name)
    shutil.copytree(ROOT / "licenses", destination / "licenses", dirs_exist_ok=True)
    copy_source_notices(destination)
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
    if package.version != RELEASE:
        raise RuntimeError("Reinstale o projeto editável antes do build: a versão instalada está desatualizada.")
    metadata = ROOT / "build" / "metadata" / f"sigilopdf-{package.version}.dist-info"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "METADATA").write_text(package.read_text("METADATA"), encoding="utf-8")
    template = (ROOT / "packaging" / "version_info.txt").read_text(encoding="utf-8")
    windows_version = tuple(int(part) for part in RELEASE.split(".")) + (0,)
    (metadata.parent / "version_info.txt").write_text(
        template.replace("$VERSION_TUPLE", repr(windows_version)).replace("$VERSION", RELEASE), encoding="utf-8",
    )
    notice = (ROOT / "packaging" / "installer_notice.txt").read_text(encoding="utf-8")
    (metadata.parent / "installer_notice.txt").write_text(notice.replace("$VERSION", RELEASE), encoding="utf-8")


if __name__ == "__main__":
    prepare_notices()
