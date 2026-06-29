"""
Custom Toggle Switch Widget — mimics the iOS-style toggle seen in the Botty Client Launcher.
"""
from PyQt6.QtWidgets import QAbstractButton
from PyQt6.QtCore import Qt, QPropertyAnimation, QRectF, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen


class ToggleSwitch(QAbstractButton):
    """Animated toggle switch (checked = blue/ON, unchecked = gray/OFF)."""

    toggled_changed = pyqtSignal(bool)

    _TRACK_W  = 44
    _TRACK_H  = 24
    _THUMB_D  = 18  # diameter
    _PADDING  = 3

    def __init__(self, parent=None, checked: bool = False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(self._TRACK_W, self._TRACK_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Animate thumb position (0.0 = left/off, 1.0 = right/on)
        self._position: float = 1.0 if checked else 0.0

        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(120)

        self.clicked.connect(self._on_clicked)

    # ---------- Qt property for animation ----------
    def _get_position(self) -> float:
        return self._position

    def _set_position(self, pos: float):
        self._position = pos
        self.update()

    position = pyqtProperty(float, _get_position, _set_position)

    # ---------- Slots ----------
    def _on_clicked(self, checked: bool):
        start = 0.0 if checked else 1.0
        end   = 1.0 if checked else 0.0
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()
        self.toggled_changed.emit(checked)

    # ---------- Paint ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self._TRACK_W, self._TRACK_H
        r    = h / 2

        # --- Track ---
        if self.isChecked():
            track_color = QColor("#0098c9")
        else:
            track_color = QColor("#c0c0c0")

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # --- Thumb ---
        thumb_x = self._PADDING + self._position * (w - self._THUMB_D - 2 * self._PADDING)
        thumb_y = (h - self._THUMB_D) / 2
        p.setBrush(QColor("#ffffff"))
        p.setPen(QPen(QColor("#00000020"), 1))
        p.drawEllipse(QRectF(thumb_x, thumb_y, self._THUMB_D, self._THUMB_D))
        p.end()

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(self._TRACK_W, self._TRACK_H)
