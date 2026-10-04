"""Downloads de fontes públicos para distribuição; nunca importado pelo app."""

import hashlib
import json
import urllib.request
import subprocess
from pathlib import Path


def fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def fetch_json(url: str) -> dict:
    return json.loads(fetch_bytes(url))


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download_source(record: dict, folder: Path) -> dict:
    if Path(record["filename"]).name != record["filename"]:
        raise RuntimeError("Nome de arquivo de fonte inválido.")
    target = folder / record["filename"]
    expected = record.get("sha256")
    if not target.exists():
        temporary = target.with_suffix(target.suffix + ".part")
        if temporary.exists():
            raise RuntimeError(f"Download parcial existente: {temporary.name}")
        try:
            with urllib.request.urlopen(record["url"], timeout=90) as response, temporary.open("xb") as stream:
                while block := response.read(1024 * 1024):
                    stream.write(block)
            temporary.rename(target)
        except Exception as error:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Falha ao baixar {record['filename']}: {error}") from error
    actual = sha256(target)
    if expected and actual != expected:
        raise RuntimeError(f"Hash incorreto para {target.name}")
    result = dict(record, sha256=actual, size=target.stat().st_size)
    print(f"Fonte verificada: {target.name} ({result['size']} bytes)", flush=True)
    return result


def download_git_source(record: dict, folder: Path) -> dict:
    target = folder / record["filename"]
    if target.exists():
        return dict(record, sha256=sha256(target), size=target.stat().st_size)
    revision = record["git_revision"]
    checkout = folder.parent / "source-checkouts" / f"{record['component']}-{revision[:12]}"
    checkout.parent.mkdir(parents=True, exist_ok=True)
    if not checkout.exists():
        subprocess.run(["git", "init", "--quiet", str(checkout)], check=True)
        subprocess.run(["git", "remote", "add", "origin", record["git_repository"]], cwd=checkout, check=True)
        subprocess.run(["git", "fetch", "--quiet", "--depth", "1", "origin", revision], cwd=checkout, check=True)
    subprocess.run(["git", "cat-file", "-e", revision + "^{commit}"], cwd=checkout, check=True)
    subprocess.run(["git", "archive", "--format=tar.gz", "--output=" + str(target), revision], cwd=checkout, check=True)
    print(f"Fonte Git verificada: {record['component']} {revision}", flush=True)
    return dict(record, sha256=sha256(target), size=target.stat().st_size)
