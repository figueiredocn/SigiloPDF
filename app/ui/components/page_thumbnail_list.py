from collections import OrderedDict

from PySide6.QtCore import QPoint, QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeyEvent, QPaintEvent, QPainter, QPen, QPixmap, QIcon, QTransform
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem

ROTATION_ROLE = Qt.ItemDataRole.UserRole + 1
MAX_ICON_BYTES = 64 * 1024 * 1024


class PageThumbnailList(QListWidget):
    order_changed = Signal()
    page_activated = Signal(int)
    thumbnail_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, QListWidgetItem] = {}
        self._icons: OrderedDict[int, int] = OrderedDict()
        self._history: list[tuple[int, ...]] = []
        self._errors: set[int] = set()
        self._points: set[int] = set()
        self._drop_target: int | None = None
        self.setObjectName("pdfPageGrid")
        self.setAccessibleName("Páginas do PDF")
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Snap)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(180, 180))
        self.setGridSize(QSize(205, 235))
        self.setMinimumHeight(270)
        self.itemDoubleClicked.connect(self._activate)
        self.verticalScrollBar().valueChanged.connect(self.request_visible)
        self.model().rowsMoved.connect(self._changed)

    def clear(self) -> None:
        self._items.clear()
        self._icons.clear()
        self._history.clear()
        self._errors.clear()
        self._points.clear()
        super().clear()

    def populate(self, total: int) -> None:
        self.clear()
        for index in range(total):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setData(ROTATION_ROLE, 0)
            self._items[index] = item
            self.addItem(item)
        self._labels()

    def order(self) -> tuple[int, ...]:
        return tuple(self.item(row).data(Qt.ItemDataRole.UserRole) for row in range(self.count()))

    def selected_pages(self) -> tuple[int, ...]:
        return tuple(item.data(Qt.ItemDataRole.UserRole) for item in sorted(self.selectedItems(), key=self.row))

    def select_pages(self, indices: tuple[int, ...]) -> None:
        blocker = QSignalBlocker(self)
        chosen = set(indices)
        for index, item in self._items.items():
            item.setSelected(index in chosen)
        del blocker

    def thumbnail(self, index: int, data: bytes) -> None:
        item = self._items.get(index)
        if item is None:
            return
        pixmap = QPixmap()
        if not data or not pixmap.loadFromData(data, "PNG"):
            self.mark_error(index, f"Não foi possível gerar a pré-visualização da página {index + 1}.")
            return
        angle = item.data(ROTATION_ROLE) or 0
        pixmap = pixmap.transformed(QTransform().rotate(angle))
        item.setIcon(QIcon(pixmap))
        self._errors.discard(index)
        self._icons[index] = pixmap.width() * pixmap.height() * 4
        self._icons.move_to_end(index)
        while sum(self._icons.values()) > MAX_ICON_BYTES:
            old, _ = self._icons.popitem(last=False)
            self._items[old].setIcon(QIcon())
        self._label(item)

    def mark_error(self, index: int, message: str) -> None:
        if index in self._items:
            self._errors.add(index)
            self._items[index].setToolTip(message)
            self._label(self._items[index])

    def request_visible(self, *_args: object) -> None:
        for index, item in self._items.items():
            if item.icon().isNull() and index not in self._errors and self.visualItemRect(item).intersects(self.viewport().rect()):
                self.thumbnail_requested.emit(index)

    def set_rotations(self, rotations: dict[int, int]) -> None:
        for index, item in self._items.items():
            angle = rotations.get(index, 0) % 360
            old = item.data(ROTATION_ROLE) or 0
            if old != angle and not item.icon().isNull():
                image = item.icon().pixmap(self.iconSize()).transformed(QTransform().rotate(angle - old))
                item.setIcon(QIcon(image))
            item.setData(ROTATION_ROLE, angle)

    def _activate(self, item: QListWidgetItem) -> None:
        self.page_activated.emit(item.data(Qt.ItemDataRole.UserRole))

    def _label(self, item: QListWidgetItem) -> None:
        row, original = self.row(item), item.data(Qt.ItemDataRole.UserRole)
        state = "\nPrévia indisponível" if original in self._errors else "\nCarregando…" if item.icon().isNull() else ""
        text = f"Página {row + 1} (original {original + 1})"
        marker = "\nDivisão após esta página" if original in self._points else ""
        item.setText(text + state + marker)
        item.setData(Qt.ItemDataRole.AccessibleTextRole, text)
        if original not in self._errors:
            item.setToolTip(text + " — Duplo clique para ampliar. Ctrl/Shift para selecionar.")

    def _labels(self) -> None:
        for row in range(self.count()):
            self._label(self.item(row))

    def set_split_points(self, indices: tuple[int, ...]) -> None:
        self._points = set(indices)
        self._labels()

    def _changed(self, *_args: object) -> None:
        self._labels()
        self.order_changed.emit()

    def _apply(self, order: tuple[int, ...], remember: bool = True) -> None:
        previous = self.order()
        if previous == order:
            return
        selected = set(self.selected_pages())
        if remember:
            self._history.append(previous)
            self._history = self._history[-20:]
        blocker = QSignalBlocker(self)
        items = {item.data(Qt.ItemDataRole.UserRole): item for item in [self.takeItem(0) for _ in range(self.count())]}
        for index in order:
            self.addItem(items[index])
            items[index].setSelected(index in selected)
        del blocker
        self._changed()

    def move_selected(self, to_start: bool) -> None:
        self.move_selection_to(0 if to_start else self.count())

    def move_step(self, direction: int) -> None:
        order = list(self.order())
        selected = set(self.selected_pages())
        positions = range(len(order)) if direction < 0 else range(len(order) - 1, -1, -1)
        for row in positions:
            adjacent = row + (-1 if direction < 0 else 1)
            if order[row] in selected and 0 <= adjacent < len(order) and order[adjacent] not in selected:
                order[row], order[adjacent] = order[adjacent], order[row]
        self._apply(tuple(order))

    def restore(self) -> None:
        self._apply(tuple(sorted(self.order())))
        self.set_rotations({})

    def undo(self) -> None:
        if self._history:
            self._apply(self._history.pop(), remember=False)

    def move_selection_to(self, target: int) -> None:
        order, selected = self.order(), set(self.selected_pages())
        target = max(0, min(target, len(order)))
        destination = target - sum(index in selected for index in order[:target])
        moving = [index for index in order if index in selected]
        remaining = [index for index in order if index not in selected]
        self._apply(tuple(remaining[:destination] + moving + remaining[destination:]))

    def _boundary(self, point: QPoint) -> int:
        item = self.itemAt(point)
        if item is None:
            return self.count()
        rect = self.visualItemRect(item)
        return self.row(item) + int(point.x() > rect.center().x())

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.source() is not self:
            event.ignore()
            return
        self._drop_target = self._boundary(event.position().toPoint())
        event.acceptProposedAction()
        self.viewport().update()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._drop_target = None
        self.viewport().update()
        super().dragLeaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._drop_target is not None and self.count():
            row = min(self._drop_target, self.count() - 1)
            rect = self.visualItemRect(self.item(row))
            x = rect.right() if self._drop_target == self.count() else rect.left()
            painter = QPainter(self.viewport())
            painter.setPen(QPen(QColor("#14A38B"), 3))
            painter.drawLine(x, rect.top(), x, rect.bottom())

    def dropEvent(self, event: QDropEvent) -> None:
        if event.source() is not self:
            event.ignore()
            return
        self.move_selection_to(self._boundary(event.position().toPoint()))
        self._drop_target = None
        self.viewport().update()
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        movable = self.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
        if movable and event.modifiers() & Qt.KeyboardModifier.AltModifier and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.move_step(-1 if event.key() == Qt.Key.Key_Left else 1)
            event.accept()
        elif movable and event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Z:
            self.undo()
            event.accept()
        else:
            super().keyPressEvent(event)
