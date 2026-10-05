"""Seleção real no Qt, sessões, cache e prévias de PDFs sintéticos."""

import time
from pathlib import Path

import pytest
from PySide6.QtCore import QBuffer, QIODevice, QPointF, Qt, QMimeData, QThread
from PySide6.QtGui import QDropEvent, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLineEdit

from app.main import create_application
from app.core import pdf_thumbnails
from app.core.split_pdf import SplitMode, SplitPdfError, split_pdf
from app.ui.components import page_thumbnail_list
from app.ui.components.page_preview_panel import PagePreviewPanel
from app.ui.components.page_thumbnail_list import PageThumbnailList
from app.ui.main_window import MainWindow
from tests.test_split_pdf import make_pdf, widths


def wait_until(condition, timeout: float = 15) -> None:
    application = create_application()
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert condition()


def image_data() -> bytes:
    create_application()
    image = QPixmap(180, 180)
    image.fill(Qt.GlobalColor.white)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def test_click_ctrl_shift_and_typed_order(tmp_path: Path) -> None:
    application = create_application()
    panel = PagePreviewPanel()
    expression = QLineEdit()
    panel.bind(expression)
    panel.resize(900, 650)
    panel.show()
    panel.load(str(make_pdf(tmp_path / "selecao.pdf", 8)), 8, external=True)
    application.processEvents()
    grid = panel.pages
    expression.setText("8,1,3")
    assert expression.text() == "8,1,3"
    assert grid.selected_pages() == (0, 2, 7)
    for index, modifiers in ((0, Qt.KeyboardModifier.NoModifier), (2, Qt.KeyboardModifier.ControlModifier)):
        QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton, modifiers, grid.visualItemRect(grid.item(index)).center())
    assert grid.selected_pages() == (0, 2)
    assert expression.text() == "1,3"
    QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, grid.visualItemRect(grid.item(0)).center())
    QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, grid.visualItemRect(grid.item(2)).center())
    assert grid.selected_pages() == (0, 1, 2)
    assert expression.text() == "1-3"
    expression.setText("0")
    assert not grid.selected_pages()
    panel.prepare_close()
    panel.close()


def test_group_drag_arrows_undo_and_stable_ids() -> None:
    application = create_application()
    grid = PageThumbnailList()
    grid.resize(900, 650)
    grid.populate(6)
    grid.show()
    application.processEvents()
    grid.select_pages((1, 3))
    grid.move_step(-1)
    assert grid.order() == (1, 0, 3, 2, 4, 5)
    grid.undo()
    grid.move_step(1)
    assert grid.order() == (0, 2, 1, 4, 3, 5)
    grid.undo()

    class InternalDrop(QDropEvent):
        def source(self):
            return grid

    rect = grid.visualItemRect(grid.item(4))
    point = rect.center()
    point.setX(rect.right() - 2)
    assert grid._boundary(point) == 5
    event = InternalDrop(QPointF(point), Qt.DropAction.MoveAction, QMimeData(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    grid.dropEvent(event)
    assert event.isAccepted()
    assert grid.order() == (0, 2, 4, 1, 3, 5)
    assert grid.selected_pages() == (1, 3)
    assert "Página 4 (original 2)" in grid.item(3).text()
    QTest.keyClick(grid, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert grid.order() == tuple(range(6))
    grid.move_selected(True)
    assert grid.order() == (1, 3, 0, 2, 4, 5)
    grid.move_selected(False)
    assert grid.order() == (0, 2, 4, 5, 1, 3)
    for _ in range(25):
        grid.move_selected(True)
        grid.move_selected(False)
    assert len(grid._history) == 20
    grid.restore()
    assert grid.order() == tuple(range(6))
    grid.close()


def test_cache_budget_and_error_placeholder(monkeypatch) -> None:
    create_application()
    monkeypatch.setattr(page_thumbnail_list, "MAX_ICON_BYTES", 180 * 180 * 4 * 2)
    grid = PageThumbnailList()
    grid.populate(4)
    data = image_data()
    for index in range(3):
        grid.thumbnail(index, data)
    assert grid.item(0).icon().isNull()
    assert len(grid._icons) == 2
    assert sum(grid._icons.values()) <= page_thumbnail_list.MAX_ICON_BYTES
    grid.mark_error(3, "Página indisponível.")
    requested = []
    grid.thumbnail_requested.connect(requested.append)
    grid.show()
    create_application().processEvents()
    grid.request_visible()
    assert 3 not in requested
    assert "Prévia indisponível" in grid.item(3).text()
    grid.close()


def test_page_failure_does_not_stop_remaining(tmp_path: Path, monkeypatch) -> None:
    path = make_pdf(tmp_path / "falha.pdf", 4)
    original = pdf_thumbnails._render

    def render(page, scale):
        if page.number == 1:
            raise RuntimeError("Falha sintética")
        return original(page, scale)

    monkeypatch.setattr(pdf_thumbnails, "_render", render)
    images, errors = [], []
    pdf_thumbnails.render_thumbnails(path, lambda index, data: images.append(index), lambda: False,
                                     failed=lambda index, message: errors.append((index, message)))
    assert images == [0, 2, 3]
    assert errors == [(1, "Não foi possível gerar a pré-visualização da página 2.")]


def test_session_change_stale_results_and_fingerprint(tmp_path: Path) -> None:
    create_application()
    panel = PagePreviewPanel()
    first = make_pdf(tmp_path / "a.pdf", 50)
    second = make_pdf(tmp_path / "b.pdf", 2)
    panel.load(str(first), 50)
    old_generation = panel.generation
    panel.load(str(second), 2)
    panel.thumbnail(old_generation, 30, image_data())
    wait_until(lambda: not panel.workers)
    assert panel.source == str(second)
    assert panel.pages.count() == 2
    assert panel.loaded == {0, 1}
    second.write_bytes(second.read_bytes() + b"\n% alterado")
    assert not panel.unchanged()
    assert not panel.pages.count()
    assert "Selecione-o novamente" in panel.status.text()
    panel.prepare_close()
    panel.close()


def test_expanded_preview_navigation_zoom_and_close(tmp_path: Path) -> None:
    application = create_application()
    panel = PagePreviewPanel(reorder=True)
    panel.show()
    panel.load(str(make_pdf(tmp_path / "ampliar.pdf", 3)), 3)
    wait_until(lambda: not panel.workers)
    panel.pages.select_pages((2,))
    panel.pages.move_selected(True)
    panel.open_page(2)
    dialog = panel.dialog
    wait_until(lambda: not dialog.workers)
    assert not dialog.image.isNull()
    assert "original 3" in dialog.title.text()
    dialog.navigate(1)
    wait_until(lambda: not dialog.workers)
    assert "original 1" in dialog.title.text()
    for _ in range(10):
        dialog.change_zoom(True)
    assert dialog.zoom == 2.0
    for _ in range(10):
        dialog.change_zoom(False)
    assert dialog.zoom == 0.25
    wait_until(lambda: not dialog.workers)
    dialog.fit()
    wait_until(lambda: not dialog.workers)
    assert 0.25 <= dialog.zoom <= 2.0
    dialog.navigate(1)
    panel.prepare_close()
    wait_until(lambda: not panel.has_pending_work())
    application.processEvents()
    assert not dialog.isVisible() if panel.dialog is not None else True
    panel.close()


def test_split_points_outputs_preserve_original(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "documento.pdf", 7)
    before = source.read_bytes()
    outputs = split_pdf(source, tmp_path, SplitMode.POINTS, "5,2,2")
    assert [widths(path) for path in outputs] == [[101, 102], [103, 104, 105], [106, 107]]
    assert [path.name for path in outputs] == ["documento_parte_001_paginas_1-2.pdf", "documento_parte_002_paginas_3-5.pdf", "documento_parte_003_paginas_6-7.pdf"]
    again = split_pdf(source, tmp_path, SplitMode.POINTS, "2,5")
    assert all(path.stem.endswith("_2") for path in again)
    assert source.read_bytes() == before


@pytest.mark.parametrize("expression", ["0", "8", "7", "3-2", "abc", "1,,2"])
def test_invalid_split_points(tmp_path: Path, expression: str) -> None:
    source = make_pdf(tmp_path / "documento.pdf", 7)
    with pytest.raises(SplitPdfError):
        split_pdf(source, tmp_path, SplitMode.POINTS, expression)
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("total", [5, 50, 200, 500])
def test_progressive_sizes_and_gui_thread(tmp_path: Path, total: int) -> None:
    application = create_application()
    panel = PagePreviewPanel()
    path = make_pdf(tmp_path / "progressivo.pdf", total)
    panel.load(str(path), total)
    threads = []
    panel.workers.copy().pop().signals.image.connect(lambda *_args: threads.append(QThread.currentThread()))
    wait_until(lambda: not panel.workers)
    assert panel.loaded == set(range(total))
    assert len(threads) == total
    assert all(thread is application.thread() for thread in threads)
    assert sum(panel.pages._icons.values()) <= page_thumbnail_list.MAX_ICON_BYTES
    panel.prepare_close()
    panel.close()


def test_restore_requires_confirmation_only_when_modified(tmp_path: Path, monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox
    create_application()
    window = MainWindow()
    page = window.reorder_page
    page.inspect_file(str(make_pdf(tmp_path / "restaurar.pdf", 3)))
    wait_until(lambda: page.worker is None)
    questions = []

    def refuse(*args):
        questions.append(args)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", refuse)
    page.restore_order()
    assert not questions
    page.pages.select_pages((2,))
    page.pages.move_selected(True)
    page.restore_order()
    assert len(questions) == 1 and page.pages.order() == (2, 0, 1)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    page.restore_order()
    assert page.pages.order() == (0, 1, 2)
    window.close()


def test_reorder_rapid_file_change_and_close(tmp_path: Path) -> None:
    create_application()
    window = MainWindow()
    window.show()
    page = window.reorder_page
    first = make_pdf(tmp_path / "primeiro.pdf", 200)
    second = make_pdf(tmp_path / "segundo.pdf", 5)
    page.inspect_file(str(first))
    page.inspect_file(str(second))
    wait_until(lambda: page.worker is None)
    assert Path(page.info.path) == second.resolve()
    assert page.pages.count() == 5 and page.loaded == 5
    page.inspect_file(str(first))
    window.close()
    wait_until(lambda: not window.isVisible() and not window._has_pending_work())


@pytest.mark.parametrize("attribute", ["reorder_page", "pdf_images_page"])
def test_queued_thumbnail_after_close_is_ignored(tmp_path: Path, attribute: str) -> None:
    create_application()
    window = MainWindow()
    page = getattr(window, attribute)
    source = make_pdf(tmp_path / "fechamento.pdf", 1)
    info = page.service.inspect(str(source))
    page.preview.prepare_close()
    # Representa sinais já enfileirados antes de o cancelamento ser observado.
    page.inspected(info)
    page.thumbnail(0, image_data())
    assert not page.pages.count() and page.loaded == 0
    window.close()
