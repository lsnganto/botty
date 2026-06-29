"""
Run Profile page — replaces the first screenshot panel.
Covers: Build dropdown, Difficulty dropdown, toggles, and Run Order dual-panel.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt

from launcher.widgets.toggle_switch import ToggleSwitch
from launcher.widgets.run_order_panel import RunOrderPanel
from launcher.config_bridge import get_bridge


BUILDS = [
    "light_sorc",
    "blizz_sorc",
    "nova_sorc",
    "hydra_sorc",
    "hammerdin",
    "fohdin",
    "trapsin",
    "barbarian",
    "necro",
    "poison_necro",
    "bone_necro",
    "basic",
    "basic_ranged",
]

DIFFICULTIES = ["hell", "nightmare", "normal"]


class RunProfilePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_values()

    # ------------------------------------------------------------------ #
    #  UI                                                                  #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scroll area wrapping all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Info banner ───────────────────────────────────────────────
        banner = QLabel("Choose the build, difficulty, and runs Botty should use.")
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        # ── Run Profile group ─────────────────────────────────────────
        profile_box = QGroupBox("Run profile")
        profile_layout = QVBoxLayout(profile_box)
        profile_layout.setSpacing(10)

        # Build + Difficulty row
        bd_row = QHBoxLayout()
        bd_row.setSpacing(16)

        build_col = QVBoxLayout()
        lbl_build = QLabel("BUILD")
        lbl_build.setObjectName("section_label")
        self._combo_build = QComboBox()
        self._combo_build.addItems(BUILDS)
        build_col.addWidget(lbl_build)
        build_col.addWidget(self._combo_build)

        diff_col = QVBoxLayout()
        lbl_diff = QLabel("DIFFICULTY")
        lbl_diff.setObjectName("section_label")
        self._combo_diff = QComboBox()
        self._combo_diff.addItems(DIFFICULTIES)
        diff_col.addWidget(lbl_diff)
        diff_col.addWidget(self._combo_diff)

        bd_row.addLayout(build_col)
        bd_row.addLayout(diff_col)
        profile_layout.addLayout(bd_row)

        # Toggles row 1: Use mercenary | CTA available
        toggle_row1 = QHBoxLayout()
        toggle_row1.setSpacing(8)
        self._toggle_merc = self._make_toggle_card("Use mercenary")
        self._toggle_cta  = self._make_toggle_card("CTA available")
        toggle_row1.addWidget(self._toggle_merc[0])
        toggle_row1.addWidget(self._toggle_cta[0])
        profile_layout.addLayout(toggle_row1)

        # Toggles row 2: Shuffle run order
        toggle_row2 = QHBoxLayout()
        self._toggle_shuffle = self._make_toggle_card("Shuffle run order each game")
        toggle_row2.addWidget(self._toggle_shuffle[0])
        toggle_row2.addStretch()
        profile_layout.addLayout(toggle_row2)

        layout.addWidget(profile_box)

        # ── Run Order group ───────────────────────────────────────────
        order_box = QGroupBox("Run order")
        order_layout = QVBoxLayout(order_box)
        order_layout.setContentsMargins(8, 12, 8, 8)

        self._run_order = RunOrderPanel()
        self._run_order.setMinimumHeight(260)
        self._run_order.order_changed.connect(self._on_order_changed)
        order_layout.addWidget(self._run_order)

        layout.addWidget(order_box)
        layout.addStretch()

        # Wire combo changes
        self._combo_build.currentTextChanged.connect(
            lambda v: get_bridge().set("char", "type", v)
        )
        self._combo_diff.currentTextChanged.connect(
            lambda v: get_bridge().set("general", "difficulty", v)
        )

    def _make_toggle_card(self, label: str) -> tuple[QWidget, ToggleSwitch]:
        """Returns (card_widget, toggle_switch)."""
        card = QWidget()
        card.setStyleSheet(
            "QWidget { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; }"
        )
        h = QHBoxLayout(card)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)
        toggle = ToggleSwitch()
        lbl = QLabel(label)
        lbl.setStyleSheet("border: none; background: transparent;")
        h.addWidget(toggle)
        h.addWidget(lbl)
        h.addStretch()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return card, toggle

    # ------------------------------------------------------------------ #
    #  Load / Save                                                         #
    # ------------------------------------------------------------------ #
    def _load_values(self):
        cfg = get_bridge()

        build = cfg.get("char", "type", "light_sorc")
        idx = self._combo_build.findText(build)
        if idx >= 0:
            self._combo_build.setCurrentIndex(idx)

        diff = cfg.get("general", "difficulty", "hell")
        idx = self._combo_diff.findText(diff)
        if idx >= 0:
            self._combo_diff.setCurrentIndex(idx)

        _, toggle_merc = self._toggle_merc
        toggle_merc.setChecked(cfg.get_bool("char", "use_merc", True))
        toggle_merc.toggled_changed.connect(
            lambda v: cfg.set_bool("char", "use_merc", v)
        )

        _, toggle_cta = self._toggle_cta
        toggle_cta.setChecked(cfg.get_bool("char", "cta_available", False))
        toggle_cta.toggled_changed.connect(
            lambda v: cfg.set_bool("char", "cta_available", v)
        )

        _, toggle_shuffle = self._toggle_shuffle
        toggle_shuffle.setChecked(cfg.get_bool("general", "randomize_runs", False))
        toggle_shuffle.toggled_changed.connect(
            lambda v: cfg.set_bool("general", "randomize_runs", v)
        )

        order_keys = cfg.get_list("routes", "order")
        self._run_order.set_order(order_keys)

    def _on_order_changed(self, keys: list[str]):
        get_bridge().set_list("routes", "order", keys)
