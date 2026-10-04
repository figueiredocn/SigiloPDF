from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QListWidget


class ImageList(QListWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setIconSize(QSize(100, 100))
        self.setMinimumHeight(260)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def move_selection_to(self, target: int) -> None:
        selected = sorted(self.row(item) for item in self.selectedItems())
        target -= sum(row < target for row in selected)
        items = [self.takeItem(row) for row in reversed(selected)]
        for offset, item in enumerate(reversed(items)):
            self.insertItem(target + offset, item)
            item.setSelected(True)

    def move_selection(self, direction: int) -> None:
        selected = sorted((self.row(item) for item in self.selectedItems()), reverse=direction > 0)
        for row in selected:
            target = row + direction
            if 0 <= target < self.count() and not self.item(target).isSelected():
                item = self.takeItem(row)
                self.insertItem(target, item)
                item.setSelected(True)

    def remove_selected(self) -> None:
        for row in sorted((self.row(item) for item in self.selectedItems()), reverse=True):
            self.takeItem(row)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.source() is not self:
            event.ignore()
            return
        index = self.indexAt(event.position().toPoint())
        self.move_selection_to(index.row() if index.isValid() else self.count())
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
