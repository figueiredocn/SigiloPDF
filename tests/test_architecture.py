import ast
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return names


def test_core_has_no_qt_imports() -> None:
    paths = list((APP_ROOT / "core").rglob("*.py"))
    assert paths
    for path in paths:
        assert not any(name.startswith(("PySide6", "app.ui", "app.services", "app.workers")) for name in imports(path))


def test_ui_does_not_import_core() -> None:
    paths = list((APP_ROOT / "ui").rglob("*.py"))
    assert paths
    for path in paths:
        assert not any(name.startswith("app.core") for name in imports(path))


def test_services_do_not_import_ui_or_qt() -> None:
    for path in (APP_ROOT / "services").rglob("*.py"):
        assert not any(name.startswith(("PySide6", "app.ui", "app.workers")) for name in imports(path))


def test_network_is_restricted_to_release_service() -> None:
    forbidden = {"socket", "requests", "urllib", "http", "httpx", "aiohttp", "ftplib", "webbrowser"}
    for path in APP_ROOT.rglob("*.py"):
        if path == APP_ROOT / "services" / "update_service.py":
            continue
        assert not any(name.split(".")[0] in forbidden or name.startswith("PySide6.QtNetwork") for name in imports(path))
