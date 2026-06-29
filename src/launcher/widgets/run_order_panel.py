"""
Dual-panel Run Order Widget
Left panel  — Available runs (with + button)
Right panel — Execution Order (with - / up / down buttons)
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal


# Map key name → display label
RUN_DISPLAY = {
    "run_trav":            "Travincal",
    "run_pindle":          "Pindle",
    "run_eldritch":        "Eldritch",
    "run_eldritch_shenk":  "Shenk / Eldritch",
    "run_nihlathak":       "Nihlathak",
    "run_arcane":          "Arcane Sanctuary",
    "run_diablo":          "Diablo (Chaos Sanctuary)",
}

ALL_RUNS = list(RUN_DISPLAY.keys())


class RunOrderPanel(QWidget):
    """
    Shows two list panels:
        Available | Execution Order
    Emits order_changed(list[str]) with the new ordered key list.
    """
    order_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._execution_keys: list[str] = []   # ordered list of run keys
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def set_order(self, keys: list[str]):
        """Populate from a list of run keys (as stored in params.ini)."""
        # Normalise: run_eldritch / run_eldritch_shenk → run_eldritch_shenk
        normalised = []
        for k in keys:
            if k in ("run_eldritch",):
                normalised.append("run_eldritch_shenk")
            else:
                normalised.append(k)
        self._execution_keys = [k for k in normalised if k in RUN_DISPLAY]
        self._refresh()

    def get_order(self) -> list[str]:
        return list(self._execution_keys)

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # ---- Left: Available ----
        left = QFrame()
        left.setObjectName("run_panel_frame")
        left.setStyleSheet(
            "#run_panel_frame { background: #fff; border: 1px solid #d8d8d8; border-radius: 4px; }"
        )
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        lbl_avail = QLabel("AVAILABLE")
        lbl_avail.setObjectName("panel_title")
        left_layout.addWidget(lbl_avail)

        self._available_list = QListWidget()
        self._available_list.setAlternatingRowColors(False)
        left_layout.addWidget(self._available_list)

        # ---- Right: Execution Order ----
        right = QFrame()
        right.setObjectName("run_panel_frame")
        right.setStyleSheet(
            "#run_panel_frame { background: #fff; border: 1px solid #d8d8d8; border-radius: 4px; }"
        )
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        lbl_exec = QLabel("EXECUTION ORDER")
        lbl_exec.setObjectName("panel_title")
        right_layout.addWidget(lbl_exec)

        self._exec_list = QListWidget()
        self._exec_list.setAlternatingRowColors(False)
        right_layout.addWidget(self._exec_list)

        # bottom buttons for right panel
        btn_row = QWidget()
        btn_row.setStyleSheet("background: #fafafa; border-top: 1px solid #e8e8e8;")
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(8, 4, 8, 4)
        btn_row_layout.setSpacing(6)

        self._btn_up   = QPushButton("↑")
        self._btn_down = QPushButton("↓")
        self._btn_remove = QPushButton("Remove")
        for b in (self._btn_up, self._btn_down, self._btn_remove):
            b.setObjectName("btn_secondary")
            b.setFixedHeight(26)

        btn_row_layout.addWidget(self._btn_up)
        btn_row_layout.addWidget(self._btn_down)
        btn_row_layout.addStretch()
        btn_row_layout.addWidget(self._btn_remove)
        right_layout.addWidget(btn_row)

        main_layout.addWidget(left)
        main_layout.addWidget(right)

        # ---- Signals ----
        self._available_list.itemDoubleClicked.connect(self._add_run)
        self._btn_up.clicked.connect(self._move_up)
        self._btn_down.clicked.connect(self._move_down)
        self._btn_remove.clicked.connect(self._remove_run)

        self._refresh()

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #
    def _refresh(self):
        """Sync both list widgets from _execution_keys."""
        self._exec_list.clear()
        for key in self._execution_keys:
            item = QListWidgetItem(RUN_DISPLAY.get(key, key))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._exec_list.addItem(item)

        self._available_list.clear()
        used = set(self._execution_keys)
        empty_msg_shown = False
        for key in ALL_RUNS:
            row_widget = _AvailableRow(key, RUN_DISPLAY[key], self._add_run_by_key)
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._available_list.addItem(item)
            self._available_list.setItemWidget(item, row_widget)

        # Show empty placeholder in exec list if empty
        if not self._execution_keys:
            placeholder = QListWidgetItem("Add at least one run to define what Botty should do.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(Qt.GlobalColor.gray)
            self._exec_list.addItem(placeholder)

    def _add_run(self, item: QListWidgetItem):
        key = item.data(Qt.ItemDataRole.UserRole)
        if key:
            self._add_run_by_key(key)

    def _add_run_by_key(self, key: str):
        self._execution_keys.append(key)
        self._refresh()
        self.order_changed.emit(self._execution_keys)

    def _move_up(self):
        row = self._exec_list.currentRow()
        if row > 0:
            self._execution_keys[row], self._execution_keys[row - 1] = \
                self._execution_keys[row - 1], self._execution_keys[row]
            self._refresh()
            self._exec_list.setCurrentRow(row - 1)
            self.order_changed.emit(self._execution_keys)

    def _move_down(self):
        row = self._exec_list.currentRow()
        if 0 <= row < len(self._execution_keys) - 1:
            self._execution_keys[row], self._execution_keys[row + 1] = \
                self._execution_keys[row + 1], self._execution_keys[row]
            self._refresh()
            self._exec_list.setCurrentRow(row + 1)
            self.order_changed.emit(self._execution_keys)

    def _remove_run(self):
        row = self._exec_list.currentRow()
        if 0 <= row < len(self._execution_keys):
            self._execution_keys.pop(row)
            self._refresh()
            self.order_changed.emit(self._execution_keys)


class _AvailableRow(QWidget):
    """A row in the Available list with a blue + button."""

    def __init__(self, key: str, label: str, add_callback, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(lbl)

        btn = QPushButton("+")
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(
            "QPushButton { background-color: #0098c9; color: #fff; border: none; "
            "border-radius: 3px; font-weight: bold; font-size: 16px; }"
            "QPushButton:hover { background-color: #007aaa; }"
        )
        btn.clicked.connect(lambda: add_callback(key))
        layout.addWidget(btn)
