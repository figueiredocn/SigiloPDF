"""Reúne fontes correspondentes às versões instaladas e bibliotecas nativas."""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from pathlib import Path

from source_downloads import download_source, fetch_bytes, fetch_json

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "build" / "corresponding-sources"
QT_MODULES = ("qtbase", "qtsvg", "qtimageformats", "qttranslations")
PYTHON_PACKAGES = (
    "pypdf", "PyMuPDF", "Pillow", "cryptography", "cffi", "pycparser",
    "PyInstaller", "pyinstaller-hooks-contrib",
)


def pypi_source(name: str) -> dict:
    release = version(name)
    data = fetch_json(f"https://pypi.org/pypi/{name}/{release}/json")
    candidates = [item for item in data["urls"] if item["packagetype"] == "sdist"]
    if len(candidates) != 1:
        raise RuntimeError(f"Fonte única não encontrada para {name} {release}.")
    item = candidates[0]
    return {"component": name, "version": release, "filename": item["filename"],
            "url": item["url"], "sha256": item["digests"]["sha256"]}


def qt_source(module: str, release: str, *, bindings: bool = False) -> dict:
    filename = f"{module}-everywhere-src-{release}.tar.xz"
    base = f"https://download.qt.io/official_releases/qt/{release.rsplit('.', 1)[0]}/{release}/submodules/"
    if bindings:
        base = f"https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{release}-src/"
    url = base + filename
    listing = fetch_bytes(url + ".mirrorlist").decode()
    match = re.search(r"SHA-256 Hash.*?<tt>([0-9a-f]{64})</tt>", listing, re.S)
    if match is None:
        raise RuntimeError(f"Checksum oficial não encontrado: {filename}")
    return {"component": module, "version": release, "filename": filename,
            "url": url, "sha256": match[1]}


def collect_sources() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(pypi_source, PYTHON_PACKAGES))
    qt = version("PySide6")
    records += [qt_source(name, qt) for name in QT_MODULES]
    records.append(qt_source("pyside-setup", qt, bindings=True))
    python = sys.version.split()[0]
    records.append({"component": "CPython", "version": python,
                    "filename": f"Python-{python}.tar.xz",
                    "url": f"https://www.python.org/ftp/python/{python}/Python-{python}.tar.xz"})
    with ThreadPoolExecutor(max_workers=4) as pool:
        complete = list(pool.map(lambda record: download_source(record, FOLDER), records))
    (FOLDER / "SOURCE_LOCK.json").write_text(
        json.dumps(complete, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    collect_sources()
