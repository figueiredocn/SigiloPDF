"""Única consulta de rede: metadados públicos da release oficial, sem contexto PDF."""

from collections.abc import Callable
import json
import ssl
import time
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

from app.core.update_info import UpdateInfo, UpdateState, compare_versions, version_key
from app.version import RELEASE_API, REPOSITORY_URL, __version__

TIMEOUT_SECONDS = 4
MAX_RESPONSE_BYTES = 256 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request: Request, file: object, code: int, message: str,
                         headers: object, new_url: str) -> None:
        raise HTTPError(request.full_url, code, "Redirecionamento recusado.", headers, file)


def fetch_latest() -> dict[str, object]:
    request = Request(RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "SigiloPDF"})
    # Sem autenticação, cookies, proxy ambiente ou redirecionamentos para outros hosts.
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
    deadline = time.monotonic() + TIMEOUT_SECONDS
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        chunks = []
        size = 0
        while True:
            chunk = response.read1(min(16384, MAX_RESPONSE_BYTES + 1 - size))
            if time.monotonic() > deadline:
                raise TimeoutError("Consulta excedeu o tempo limite.")
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise ValueError("Resposta muito grande.")
            chunks.append(chunk)
            if not chunk:
                break
    data = json.loads(b"".join(chunks))
    if not isinstance(data, dict):
        raise ValueError("Resposta inválida.")
    return data


class UpdateService:
    def __init__(self, current_version: str = __version__, fetch: Callable[[], dict[str, object]] = fetch_latest) -> None:
        self.current_version, self.fetch = current_version, fetch

    def check(self) -> UpdateInfo:
        try:
            data = self.fetch()
            tag = data["tag_name"]
            if not isinstance(tag, str) or data.get("draft") is not False or data.get("prerelease") is not False:
                raise ValueError("Release inválida.")
            version_key(tag)
            url = f"{REPOSITORY_URL}/releases/tag/{tag}"
            if data.get("html_url") != url:
                raise ValueError("Origem inválida.")
            return UpdateInfo(self.current_version, compare_versions(self.current_version, tag),
                              tag.removeprefix("v"), str(data.get("name") or tag)[:200], url,
                              str(data.get("published_at") or "")[:40], str(data.get("body") or "")[:20000])
        except Exception:
            return UpdateInfo(self.current_version, UpdateState.CHECK_FAILED)
