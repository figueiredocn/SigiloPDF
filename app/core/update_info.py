"""Estados e comparação SemVer, sem rede, arquivos ou interface."""

from dataclasses import dataclass
from enum import Enum
import re


class UpdateState(str, Enum):
    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    CHECK_FAILED = "CHECK_FAILED"
    DEV_VERSION = "DEV_VERSION"


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    state: UpdateState
    latest_version: str = ""
    release_name: str = ""
    release_url: str = ""
    published_at: str = ""
    release_notes: str = ""

    @property
    def update_available(self) -> bool:
        return self.state == UpdateState.UPDATE_AVAILABLE


def version_key(value: str) -> tuple[int, int, int, int, tuple[tuple[int, object], ...]]:
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([\w.-]+))?(?:\+([\w.-]+))?", value, re.ASCII)
    if not match:
        raise ValueError("Versão inválida.")
    major, minor, patch, prerelease, build = match.groups()
    identifiers = tuple(prerelease.split(".")) if prerelease else ()
    for part in (*identifiers, *(build.split(".") if build else ())):
        if not re.fullmatch(r"[A-Za-z0-9-]+", part):
            raise ValueError("Versão inválida.")
    if any(part.isdigit() and len(part) > 1 and part.startswith("0") for part in identifiers):
        raise ValueError("Versão inválida.")
    ordering = tuple((0, int(part)) if part.isdigit() else (1, part) for part in identifiers)
    return int(major), int(minor), int(patch), int(not prerelease), ordering


def compare_versions(current: str, latest: str) -> UpdateState:
    installed, published = version_key(current), version_key(latest)
    if installed < published:
        return UpdateState.UPDATE_AVAILABLE
    return UpdateState.UP_TO_DATE if installed == published else UpdateState.DEV_VERSION
