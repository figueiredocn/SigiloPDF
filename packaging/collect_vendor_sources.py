"""Fontes nativas e crates Rust usadas pelas bibliotecas da distribuição."""

import json
import tarfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from source_downloads import download_source, fetch_bytes

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "build" / "corresponding-sources"


def github_source(component: str, repository: str, tag: str, release: str) -> dict:
    return {"component": component, "version": release,
            "filename": f"{component}-{release}.tar.gz",
            "url": f"https://codeload.github.com/{repository}/tar.gz/refs/tags/{tag}"}


def rust_sources() -> list[dict]:
    with tarfile.open(FOLDER / "cryptography-50.0.2.tar.gz") as archive:
        member = next(m for m in archive.getmembers() if m.name.endswith("/Cargo.lock"))
        lock = tomllib.loads(archive.extractfile(member).read().decode())
    records = []
    for package in lock["package"]:
        if "source" not in package:
            continue
        if not package["source"].startswith("registry+"):
            raise RuntimeError("Dependência Rust Git exige revisão antes de publicar.")
        name, release = package["name"], package["version"]
        filename = f"{name}-{release}.crate"
        records.append({"component": f"rust-{name}", "version": release,
                        "filename": filename, "sha256": package["checksum"],
                        "url": f"https://static.crates.io/crates/{name}/{filename}"})
    return records


def pillow_sources() -> list[dict]:
    data = fetch_bytes("https://raw.githubusercontent.com/python-pillow/Pillow/12.3.0/.github/dependencies.json")
    versions = json.loads(data)
    records = [github_source("Pillow-complete", "python-pillow/Pillow", "12.3.0", "12.3.0")]
    repositories = (
        ("jpegturbo", "libjpeg-turbo", "libjpeg-turbo/libjpeg-turbo", "{version}"),
        ("zlib-ng", "pillow-zlib-ng", "zlib-ng/zlib-ng", "{version}"),
        ("xz", "pillow-xz", "tukaani-project/xz", "v{version}"),
        ("brotli", "brotli", "google/brotli", "v{version}"),
        ("freetype", "freetype", "freetype/freetype", "VER-{dash}"),
        ("lcms2", "lcms2", "mm2/Little-CMS", "lcms{version}"),
        ("openjpeg", "openjpeg", "uclouvain/openjpeg", "v{version}"),
        ("harfbuzz", "harfbuzz", "harfbuzz/harfbuzz", "{version}"),
        ("fribidi", "fribidi", "fribidi/fribidi", "v{version}"),
        ("libavif", "libavif", "AOMediaCodec/libavif", "v{version}"),
    )
    for key, component, repository, template in repositories:
        release = versions[key]
        tag = template.format(version=release, dash=release.replace(".", "-"))
        records.append(github_source(component, repository, tag, release))
    for component, base, release in (
        ("libwebp", "https://storage.googleapis.com/downloads.webmproject.org/releases/webp/", versions["libwebp"]),
        ("tiff", "https://download.osgeo.org/libtiff/", versions["tiff"]),
    ):
        filename = f"{component}-{release}.tar.gz"
        records.append({"component": component, "version": release, "filename": filename, "url": base + filename})
    return records


def python_sources() -> list[dict]:
    records = []
    for branch in ("bzip2-1.0.8", "libffi-3.4.4", "xz-5.2.5", "zlib-ng-2.2.4", "openssl-3.5.7"):
        records.append({"component": f"cpython-{branch}", "version": branch.rsplit("-", 1)[1],
                        "filename": f"cpython-{branch}.tar.gz",
                        "url": f"https://codeload.github.com/python/cpython-source-deps/tar.gz/refs/tags/{branch}"})
    return records


def collect_vendor_sources() -> None:
    records = rust_sources() + pillow_sources() + python_sources()
    records += [
        {"component": "MuPDF", "version": "1.28.2", "filename": "mupdf-1.28.2-source.tar.gz",
         "url": "https://mupdf.com/downloads/archive/mupdf-1.28.2-source.tar.gz"},
        github_source("openssl-cryptography", "openssl/openssl", "openssl-4.0.3", "4.0.3"),
        github_source("zstd", "facebook/zstd", "v1.5.7", "1.5.7"),
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        complete = list(pool.map(lambda record: download_source(record, FOLDER), records))
    (FOLDER / "VENDOR_SOURCE_LOCK.json").write_text(
        json.dumps(complete, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    collect_vendor_sources()
