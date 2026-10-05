"""Configuração local restrita a três campos, sem histórico de documentos."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


@dataclass
class UpdatePreferences:
    automatic: bool = False
    last_check: float = 0.0
    latest_version: str = ""

    def due(self, now: float) -> bool:
        return self.automatic and (not self.last_check or now - self.last_check >= 86400)


class UpdatePreferenceStore:
    def __init__(self, path: Path | None = None) -> None:
        root = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        self.path = path or root / "SigiloPDF" / "update_preferences.json"

    def load(self) -> UpdatePreferences:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            automatic, last, latest = data["automatic"], data["last_check"], data["latest_version"]
            if type(automatic) is not bool or type(last) not in (int, float) or not 0 <= last < 1e12 or not isinstance(latest, str):
                raise ValueError("Configuração inválida.")
            return UpdatePreferences(automatic, last, latest[:100])
        except (OSError, ValueError, TypeError, KeyError):
            return UpdatePreferences()

    def save(self, preferences: UpdatePreferences) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(asdict(preferences), stream, ensure_ascii=False)
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
