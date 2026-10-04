# Build Windows em pasta: bibliotecas compartilhadas permanecem substituíveis.
from pathlib import Path
import os
import sys

from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent
# Não coletar DLLs de outras ferramentas presentes no PATH do desenvolvedor.
# Qt usa a ICU do Windows; uma ICU de Poppler, por exemplo, tem ABI diferente.
windows = os.environ["SystemRoot"]
os.environ["PATH"] = os.pathsep.join((
    sys.base_prefix, str(Path(sys.base_prefix) / "DLLs"),
    str(Path(windows) / "System32"), windows,
))
data = collect_data_files("app.ui.brand_assets")
data += collect_data_files("app.ui.styles")
data += [(str(root / "build" / "metadata" / "sigilopdf-1.0.0.dist-info"), "sigilopdf-1.0.0.dist-info")]
data += [(str(root / "build" / "notices"), "licencas")]

analysis = Analysis(
    [str(root / "packaging" / "launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=data,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    noarchive=False,
)
# A análise automática de importlib.metadata também coleta dados do pacote
# editável. Remover o arquivo mesmo se um hook o acrescentar novamente.
analysis.datas = [item for item in analysis.datas if not item[0].endswith("direct_url.json")]
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="SigiloPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "app" / "ui" / "brand_assets" / "sigilopdf.ico"),
    version=str(root / "packaging" / "version_info.txt"),
)
coll = COLLECT(
    exe, analysis.binaries, analysis.datas,
    strip=False, upx=False, name="SigiloPDF",
)
