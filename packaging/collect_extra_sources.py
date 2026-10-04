"""Subdependências nativas dos codecs AVIF e do FreeType."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from collect_vendor_sources import github_source
from source_downloads import download_source, download_git_source

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "build" / "corresponding-sources"


def collect_extra_sources() -> None:
    records = [
        {"component": "libaom", "version": "3.14.1", "filename": "libaom-3.14.1.tar.gz",
         "url": "https://aomedia.googlesource.com/aom", "git_repository": "https://aomedia.googlesource.com/aom.git",
         "git_revision": "03087864cf4bea6abb0d28f95cf7843511413d8f"},
        {"component": "libyuv", "version": "644251f252a84bf8ce91ff0aca86a9b16b069ab8", "filename": "libyuv-644251f252a84bf8ce91ff0aca86a9b16b069ab8.tar.gz",
         "url": "https://chromium.googlesource.com/libyuv/libyuv", "git_repository": "https://chromium.googlesource.com/libyuv/libyuv",
         "git_revision": "644251f252a84bf8ce91ff0aca86a9b16b069ab8"},
        github_source("dav1d", "videolan/dav1d", "1.5.3", "1.5.3"),
        {"component": "dlg", "version": "395ccad2c1e0daae535c4d20bb0a3f2424648e17", "filename": "dlg-395ccad2c1e0daae535c4d20bb0a3f2424648e17.tar.gz",
         "url": "https://codeload.github.com/nyorain/dlg/tar.gz/395ccad2c1e0daae535c4d20bb0a3f2424648e17"},
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        complete = list(pool.map(lambda record: download_git_source(record, FOLDER) if "git_repository" in record else download_source(record, FOLDER), records))
    (FOLDER / "EXTRA_SOURCE_LOCK.json").write_text(
        json.dumps(complete, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    collect_extra_sources()
