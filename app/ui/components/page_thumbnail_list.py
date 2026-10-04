from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDropEvent, QIcon, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem


class PageThumbnailList(QListWidget):
    order_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Snap)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(180, 180))
        self.setGridSize(QSize(205, 230))
        self.setMinimumHeight(280)
        self.model().rowsMoved.connect(self._changed)

    def populate(self, total: int) -> None:
        self.clear()
        for index in range(total):
            item = QListWidgetItem(f"Página {index + 1}\nCarregando…")
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.addItem(item)

    def order(self) -> tuple[int, ...]:
        return tuple(self.item(row).data(Qt.ItemDataRole.UserRole) for row in range(self.count()))

    def thumbnail(self, index: int, data: bytes) -> None:
        for row in range(self.count()):
            item = self.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == index:
                pixmap = QPixmap()
                pixmap.loadFromData(data, "PNG")
                item.setIcon(QIcon(pixmap))
                item.setText(f"Página {row + 1} (original {index + 1})")
                break

    def _labels(self) -> None:
        for row in range(self.count()):
            item = self.item(row)
            original = item.data(Qt.ItemDataRole.UserRole) + 1
            loading = "\nCarregando…" if item.icon().isNull() else ""
            item.setText(f"Página {row + 1} (original {original}){loading}")

    def _changed(self, *args: object) -> None:
        self._labels()
        self.order_changed.emit()

    def move_selected(self, to_start: bool) -> None:
        selected = sorted(self.row(item) for item in self.selectedItems())
        items = [self.takeItem(row) for row in reversed(selected)]
        items.reverse()
        for offset, item in enumerate(items):
            self.insertItem(offset if to_start else self.count(), item)
            item.setSelected(True)
        self._changed()

    def restore(self) -> None:
        items = [self.takeItem(0) for _ in range(self.count())]
        for item in sorted(items, key=lambda item: item.data(Qt.ItemDataRole.UserRole)):
            self.addItem(item)
        self._changed()

    def move_selection_to(self, target: int) -> None:
        selected = sorted(self.row(item) for item in self.selectedItems())
        if not selected:
            return
        target -= sum(row < target for row in selected)
        items = [self.takeItem(row) for row in reversed(selected)]
        for offset, item in enumerate(reversed(items)):
            self.insertItem(target + offset, item)
            item.setSelected(True)
        self._changed()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.source() is not self:
            event.ignore()
            return
        index = self.indexAt(event.position().toPoint())
        self.move_selection_to(index.row() if index.isValid() else self.count())
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
