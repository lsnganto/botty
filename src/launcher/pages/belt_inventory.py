"""
Belt & Inventory page.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QSpinBox, QScrollArea
)
from launcher.config_bridge import get_bridge


class BeltInventoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        banner = QLabel("Configure belt layout and inventory slot usage.")
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        # ── Belt ──────────────────────────────────────────────────────
        belt_box = QGroupBox("Belt")
        belt_form = QFormLayout(belt_box)
        belt_form.setSpacing(8)
        belt_form.setContentsMargins(12, 16, 12, 12)

        self._belt_rows   = self._spin(1, 4)
        self._belt_hp_col = self._spin(0, 4)
        self._belt_mp_col = self._spin(0, 4)
        self._belt_rj_col = self._spin(0, 4)

        belt_form.addRow("Belt rows:", self._belt_rows)
        belt_form.addRow("HP potion columns:", self._belt_hp_col)
        belt_form.addRow("MP potion columns:", self._belt_mp_col)
        belt_form.addRow("Rejuv potion columns:", self._belt_rj_col)
        layout.addWidget(belt_box)

        # ── Inventory ─────────────────────────────────────────────────
        inv_box = QGroupBox("Inventory")
        inv_form = QFormLayout(inv_box)
        inv_form.setSpacing(8)
        inv_form.setContentsMargins(12, 16, 12, 12)

        self._num_loot_cols  = self._spin(1, 10)
        self._runs_per_stash = self._spin(0, 100)
        self._runs_per_repair = self._spin(0, 200)

        inv_form.addRow("Loot columns (from left):", self._num_loot_cols)
        inv_form.addRow("Runs per stash (0 = disabled):", self._runs_per_stash)
        inv_form.addRow("Runs per repair (0 = disabled):", self._runs_per_repair)
        layout.addWidget(inv_box)

        layout.addStretch()

        # Wire signals
        self._belt_rows.valueChanged.connect(lambda v: get_bridge().set("char", "belt_rows", v))
        self._belt_hp_col.valueChanged.connect(lambda v: get_bridge().set("char", "belt_hp_columns", v))
        self._belt_mp_col.valueChanged.connect(lambda v: get_bridge().set("char", "belt_mp_columns", v))
        self._belt_rj_col.valueChanged.connect(lambda v: get_bridge().set("char", "belt_rejuv_columns", v))
        self._num_loot_cols.valueChanged.connect(lambda v: get_bridge().set("char", "num_loot_columns", v))
        self._runs_per_stash.valueChanged.connect(lambda v: get_bridge().set("char", "runs_per_stash", v))
        self._runs_per_repair.valueChanged.connect(lambda v: get_bridge().set("char", "runs_per_repair", v))

    def _spin(self, min_val: int, max_val: int) -> QSpinBox:
        s = QSpinBox()
        s.setRange(min_val, max_val)
        s.setMaximumWidth(100)
        return s

    def _load_values(self):
        cfg = get_bridge()
        self._belt_rows.setValue(cfg.get_int("char", "belt_rows", 4))
        self._belt_hp_col.setValue(cfg.get_int("char", "belt_hp_columns", 1))
        self._belt_mp_col.setValue(cfg.get_int("char", "belt_mp_columns", 1))
        self._belt_rj_col.setValue(cfg.get_int("char", "belt_rejuv_columns", 2))
        self._num_loot_cols.setValue(cfg.get_int("char", "num_loot_columns", 5))
        self._runs_per_stash.setValue(cfg.get_int("char", "runs_per_stash", 4))
        self._runs_per_repair.setValue(cfg.get_int("char", "runs_per_repair", 0))
