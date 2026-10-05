from PySide6.QtCore import QThreadPool, Qt, Slot
from PySide6.QtGui import QCloseEvent, QKeySequence, QPixmap, QShortcut, QTransform
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.ui.branding import brand_icon
from app.workers.preview_worker import PreviewWorker

ZOOMS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


class PdfPreviewDialog(QDialog):
    def __init__(self, source: str, order: tuple[int, ...], index: int,
                 rotations: dict[int, int], parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pré-visualização do PDF")
        self.setWindowIcon(brand_icon())
        self.resize(780, 700)
        self.source, self.order, self.rotations = source, order, rotations
        self.position = order.index(index)
        self.zoom, self.generation = 1.0, 0
        self.workers: set[PreviewWorker] = set()
        self.image = QPixmap()
        self.closed = False
        layout = QVBoxLayout(self)
        self.title = QLabel()
        layout.addWidget(self.title)
        controls = QHBoxLayout()
        self.previous = QPushButton("← Página anterior")
        self.next = QPushButton("Próxima página →")
        self.percent = QLabel("100%")
        for text, callback in (("−", lambda: self.change_zoom(False)), ("+", lambda: self.change_zoom(True)),
                               ("Ajustar à janela", self.fit)):
            button = QPushButton(text)
            button.clicked.connect(callback)
            controls.addWidget(button)
        controls.addWidget(self.percent)
        self.previous.clicked.connect(lambda: self.navigate(-1))
        self.next.clicked.connect(lambda: self.navigate(1))
        controls.addWidget(self.previous)
        controls.addWidget(self.next)
        layout.addLayout(controls)
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)
        self.status = QLabel("Renderizando localmente…")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        close = QPushButton("Fechar")
        close.clicked.connect(self.close)
        layout.addWidget(close)
        for key, delta in (("Left", -1), ("Right", 1)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda step=delta: self.navigate(step))
        self.request()

    def request(self) -> None:
        self.generation += 1
        for worker in self.workers:
            worker.cancelled.set()
        index = self.order[self.position]
        self.title.setText(f"Página {self.position + 1} de {len(self.order)} — original {index + 1}")
        self.percent.setText(f"{round(self.zoom * 100)}%")
        self.previous.setEnabled(self.position > 0)
        self.next.setEnabled(self.position + 1 < len(self.order))
        self.status.setText("Renderizando localmente…")
        worker = PreviewWorker(self.source, self.generation, index, self.zoom)
        self.workers.add(worker)
        worker.signals.image.connect(self.rendered)
        worker.signals.failed.connect(self.failed)
        worker.signals.finished.connect(self.worker_finished)
        QThreadPool.globalInstance().start(worker, 1)

    @Slot(int, int, bytes)
    def rendered(self, generation: int, index: int, data: bytes) -> None:
        if generation != self.generation:
            return
        image = QPixmap()
        if not image.loadFromData(data, "PNG"):
            self.failed(generation, index, "Não foi possível exibir esta página.")
            return
        self.image = image.transformed(QTransform().rotate(self.rotations.get(index, 0)))
        self.canvas.setPixmap(self.image)
        self.canvas.resize(self.image.size())
        self.status.setText("Pré-visualização local. O arquivo original permanece inalterado.")

    @Slot(int, int, str)
    def failed(self, generation: int, index: int, message: str) -> None:
        if generation == self.generation:
            self.status.setText(message)
            self.canvas.clear()
            self.image = QPixmap()

    @Slot(object)
    def worker_finished(self, worker: PreviewWorker) -> None:
        self.workers.discard(worker)
        if self.closed and not self.workers:
            self.deleteLater()

    def navigate(self, direction: int) -> None:
        position = self.position + direction
        if 0 <= position < len(self.order):
            self.position = position
            self.request()

    def change_zoom(self, increase: bool) -> None:
        choices = [zoom for zoom in ZOOMS if zoom > self.zoom] if increase else [zoom for zoom in ZOOMS if zoom < self.zoom]
        if choices:
            self.zoom = min(choices) if increase else max(choices)
            self.request()

    def fit(self) -> None:
        if not self.image.isNull():
            factor = min(self.scroll.viewport().width() / self.image.width(), self.scroll.viewport().height() / self.image.height())
            self.zoom = max(0.25, min(2.0, self.zoom * factor))
            self.request()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed = True
        self.generation += 1
        for worker in self.workers:
            worker.cancelled.set()
        self.canvas.clear()
        self.image = QPixmap()
        if not self.workers:
            self.deleteLater()
        super().closeEvent(event)
