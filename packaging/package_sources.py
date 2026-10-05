"""Empacota apenas fontes públicos explicitamente inventariados."""

import json
import subprocess
import sys
import runpy
import zipfile
from pathlib import Path

from source_downloads import sha256

ROOT = Path(__file__).resolve().parent.parent
RELEASE = runpy.run_path(str(ROOT / "app" / "version.py"))["__version__"]
SOURCES = ROOT / "build" / "corresponding-sources"


def package_sources(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    manifests = ("SOURCE_LOCK.json", "VENDOR_SOURCE_LOCK.json", "EXTRA_SOURCE_LOCK.json")
    records = []
    for name in manifests:
        records.extend(json.loads((SOURCES / name).read_text(encoding="utf-8")))
    for record in records:
        path = SOURCES / record["filename"]
        if sha256(path) != record["sha256"]:
            raise RuntimeError(f"Fonte alterada: {path.name}")
    dependency_zip = output / f"SigiloPDF-{RELEASE}-fontes-dependencias.zip"
    with zipfile.ZipFile(dependency_zip, "x", compression=zipfile.ZIP_STORED) as archive:
        for record in records:
            archive.write(SOURCES / record["filename"], record["filename"])
        for name in manifests:
            archive.write(SOURCES / name, name)
        archive.write(ROOT / "docs" / "FONTES_CORRESPONDENTES.md", "LEIA-ME.md")
    application_zip = output / f"SigiloPDF-{RELEASE}-fontes-aplicacao.zip"
    if application_zip.exists():
        raise RuntimeError("O arquivo de fontes da aplicação já existe.")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subprocess.run(["git", "archive", "--format=zip", "--prefix=SigiloPDF/", f"--output={application_zip}", revision], cwd=ROOT, check=True)
    with zipfile.ZipFile(application_zip, "a") as archive:
        archive.writestr("SigiloPDF/SOURCE_REVISION.txt", revision + "\n")
    print(f"Fontes da aplicação: {revision}; dependências: {len(records)} arquivos verificados.")


if __name__ == "__main__":
    package_sources(Path(sys.argv[1]).resolve())
