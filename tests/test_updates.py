import json
from pathlib import Path
from threading import Event
import time

import pytest
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow

from app.main import create_application
from app.services import update_service
from app.services.update_preferences import UpdatePreferences, UpdatePreferenceStore
from app.services.update_service import UpdateService, UpdateState, compare_versions
from app.ui.components.update_controller import UpdateController
from app.version import RELEASE_API, REPOSITORY_URL, __version__


def release(version: str = "v1.1.0") -> dict[str, object]:
    return {"tag_name": version, "html_url": f"{REPOSITORY_URL}/releases/tag/{version}",
            "draft": False, "prerelease": False, "name": "SigiloPDF", "body": "Novidades locais.",
            "published_at": "2026-10-05T12:00:00Z"}


@pytest.mark.parametrize("current,latest,state", [
    ("1.0.0", "v1.1.0", UpdateState.UPDATE_AVAILABLE),
    ("1.1.0", "v1.1.0", UpdateState.UP_TO_DATE),
    ("1.2.0", "v1.1.0", UpdateState.DEV_VERSION),
    ("1.9.0", "1.10.0", UpdateState.UPDATE_AVAILABLE),
    ("1.99.99", "2.0.0", UpdateState.UPDATE_AVAILABLE),
    ("1.1.0", "1.1.1", UpdateState.UPDATE_AVAILABLE),
    ("1.1.0-beta.9", "1.1.0-beta.10", UpdateState.UPDATE_AVAILABLE),
    ("1.1.0-rc.1", "1.1.0", UpdateState.UPDATE_AVAILABLE),
    ("1.1.0+build.1", "1.1.0+build.2", UpdateState.UP_TO_DATE),
])
def test_semantic_comparison(current: str, latest: str, state: UpdateState) -> None:
    assert compare_versions(current, latest) == state


@pytest.mark.parametrize("version", ["1.1", "01.1.0", "1.1.0-01", "1.1.0-a..b", "1.1.0-a_b", "1.1.0/path"])
def test_invalid_version(version: str) -> None:
    assert UpdateService(fetch=lambda: release(version)).check().state == UpdateState.CHECK_FAILED


@pytest.mark.parametrize("current,state", [("1.0.0", UpdateState.UPDATE_AVAILABLE), ("1.1.0", UpdateState.UP_TO_DATE), ("1.2.0", UpdateState.DEV_VERSION)])
def test_service_states(current: str, state: UpdateState) -> None:
    info = UpdateService(current, lambda: release()).check()
    assert info.state == state and info.latest_version == "1.1.0"
    assert info.update_available == (state == UpdateState.UPDATE_AVAILABLE)


def test_offline_and_untrusted_release() -> None:
    def offline():
        raise TimeoutError("Sem conexão sintética")
    assert UpdateService(fetch=offline).check().state == UpdateState.CHECK_FAILED
    for field, value in (("html_url", "https://example.invalid"), ("draft", True), ("prerelease", True)):
        data = release()
        data[field] = value
        assert UpdateService(fetch=lambda: data).check().state == UpdateState.CHECK_FAILED


def test_minimal_request_and_bounded_response(monkeypatch) -> None:
    observed = []

    class Response:
        def __init__(self):
            self.body = json.dumps(release()).encode()
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            pass
        def read1(self, count):
            body, self.body = self.body[:count], self.body[count:]
            return body

    class Opener:
        def open(self, request, timeout):
            observed.append((request, timeout))
            return Response()

    monkeypatch.setattr(update_service, "build_opener", lambda *handlers: Opener())
    assert update_service.fetch_latest()["tag_name"] == "v1.1.0"
    request, timeout = observed[0]
    assert request.full_url == RELEASE_API and request.get_method() == "GET"
    assert request.data is None
    assert dict(request.header_items()) == {"Accept": "application/vnd.github+json", "User-agent": "SigiloPDF"}
    assert timeout == 4
    monkeypatch.setattr(update_service, "MAX_RESPONSE_BYTES", 10)
    with pytest.raises(ValueError, match="grande"):
        update_service.fetch_latest()


def test_preferences_only_store_allowed_fields(tmp_path: Path) -> None:
    store = UpdatePreferenceStore(tmp_path / "preferences.json")
    preferences = store.load()
    assert not preferences.automatic and not store.path.exists()
    preferences.automatic = True
    preferences.last_check = 100
    preferences.latest_version = "1.1.0"
    store.save(preferences)
    assert set(json.loads(store.path.read_text())) == {"automatic", "last_check", "latest_version"}
    assert store.load() == preferences
    assert not preferences.due(100 + 86399)
    assert preferences.due(100 + 86400)
    assert not list(tmp_path.glob("tmp*"))


@pytest.mark.parametrize("data", ["{}", "null", "invalid", '{"automatic":"yes","last_check":0,"latest_version":""}'])
def test_bad_preferences_default_to_off(tmp_path: Path, data: str) -> None:
    path = tmp_path / "preferences.json"
    path.write_text(data)
    assert UpdatePreferenceStore(path).load() == UpdatePreferences()


def wait_until(condition) -> None:
    application = create_application()
    deadline = time.monotonic() + 5
    while not condition() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert condition()


def test_manual_ui_no_automatic_download_and_daily_limit(tmp_path: Path, monkeypatch) -> None:
    create_application()
    opened, calls = [], []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()))
    service = UpdateService("1.0.0", lambda: calls.append(1) or release())
    window = QMainWindow()
    controller = UpdateController(window, UpdatePreferenceStore(tmp_path / "prefs.json"), service)
    controller.check_automatic()
    assert not calls
    controller.check_manual()
    wait_until(lambda: controller.worker is None)
    dialog = controller.dialog
    assert "Uma nova versão" in dialog.status.text() and not opened
    dialog.download.click()
    assert opened == [f"{REPOSITORY_URL}/releases/tag/v1.1.0"]
    dialog.automatic.setChecked(True)
    controller.check_automatic()
    assert len(calls) == 1
    dialog.automatic.setChecked(False)
    assert not controller.store.load().automatic
    controller.prepare_close()
    window.close()


def test_update_worker_does_not_block_gui_or_share_pdf_pool(tmp_path: Path) -> None:
    from PySide6.QtCore import QThreadPool
    application = create_application()
    started, finish = Event(), Event()
    def delayed():
        started.set()
        assert finish.wait(3)
        return release()
    window = QMainWindow()
    controller = UpdateController(window, UpdatePreferenceStore(tmp_path / "prefs.json"), UpdateService(fetch=delayed))
    try:
        controller.check_manual()
        assert started.wait(2)
        application.processEvents()
        assert controller.pool is not QThreadPool.globalInstance()
        assert controller.dialog.isVisible()
        controller.prepare_close()
        assert controller.pending()
    finally:
        finish.set()
        wait_until(lambda: not controller.pending())
        window.close()


def test_ui_version_matches_package() -> None:
    from importlib.metadata import version
    from app.ui.components.about_dialog import AboutDialog
    from PySide6.QtWidgets import QLabel
    create_application()
    dialog = AboutDialog()
    assert version("sigilopdf") == __version__
    assert any(f"Versão: {__version__}" in label.text() for label in dialog.findChildren(QLabel))
    dialog.close()
