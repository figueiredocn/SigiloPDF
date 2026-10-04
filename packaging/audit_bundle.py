"""Auditoria local do pacote antes de criar arquivos de distribuição."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def audit_bundle(bundle: Path) -> None:
    if not (bundle / "SigiloPDF.exe").is_file():
        raise RuntimeError("Executável não encontrado.")
    personal_path = str(Path.home())
    markers = (
        personal_path.encode("utf-8"),
        personal_path.replace("\\", "/").encode("utf-8"),
        personal_path.encode("utf-16-le"),
    )
    for file in bundle.rglob("*"):
        if not file.is_file():
            continue
        if file.name == "direct_url.json" or file.suffix.lower() in (".pdf", ".log", ".tmp"):
            raise RuntimeError(f"Arquivo indevido no pacote: {file.relative_to(bundle)}")
        if any(marker in file.read_bytes() for marker in markers):
            raise RuntimeError(f"Caminho pessoal encontrado: {file.relative_to(bundle)}")
    internal = bundle / "_internal"
    # Esta distribuição usa a ICU fornecida pelo Windows, não outra ICU do PATH.
    if (internal / "icuuc.dll").exists():
        raise RuntimeError("ICU externa inesperada no pacote Windows.")
    print("Pacote revisado: sem documentos, metadados de instalação ou caminhos pessoais identificados.")


if __name__ == "__main__":
    audit_bundle(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "SigiloPDF")
