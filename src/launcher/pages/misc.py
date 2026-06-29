"""
Misc page — miscellaneous char options.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QSpinBox, QLineEdit, QScrollArea, QHBoxLayout, QCheckBox
)
from launcher.config_bridge import get_bridge
from launcher.widgets.toggle_switch import ToggleSwitch


class MiscPage(QWidget):
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

        banner = QLabel("Miscellaneous options for run behaviour, stashing, and selling.")
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        # ── Run behaviour ─────────────────────────────────────────────
        run_box = QGroupBox("Run behaviour")
        run_form = QFormLayout(run_box)
        run_form.setSpacing(8)
        run_form.setContentsMargins(12, 16, 12, 12)

        self._tog_open_chests  = ToggleSwitch()
        self._tog_pre_buff     = ToggleSwitch()
        self._tog_no_pickup    = ToggleSwitch()
        self._tog_safer        = ToggleSwitch()
        self._tog_fill_shared  = ToggleSwitch()
        self._tog_stash_gold   = ToggleSwitch()
        self._tog_sell_junk    = ToggleSwitch()

        run_form.addRow("Open chests:", self._tog_open_chests)
        run_form.addRow("Pre-buff every run:", self._tog_pre_buff)
        run_form.addRow("Enable no-pickup mode:", self._tog_no_pickup)
        run_form.addRow("Safer routines (HC):", self._tog_safer)
        run_form.addRow("Fill shared stash first:", self._tog_fill_shared)
        run_form.addRow("Stash gold:", self._tog_stash_gold)
        run_form.addRow("Sell junk:", self._tog_sell_junk)
        layout.addWidget(run_box)

        # ── Gamble / Misc ─────────────────────────────────────────────
        misc_box = QGroupBox("Gamble / Other")
        misc_form = QFormLayout(misc_box)
        misc_form.setSpacing(8)
        misc_form.setContentsMargins(12, 16, 12, 12)

        self._gamble_items = QLineEdit()
        self._gamble_items.setPlaceholderText("e.g. circlet, ring, amulet")
        self._casting_frames = QSpinBox()
        self._casting_frames.setRange(1, 20)
        self._casting_frames.setMaximumWidth(80)
        self._max_game_len = QSpinBox()
        self._max_game_len.setRange(60, 1200)
        self._max_game_len.setSuffix(" s")
        self._max_game_len.setMaximumWidth(100)
        self._max_fails = QSpinBox()
        self._max_fails.setRange(1, 50)
        self._max_fails.setMaximumWidth(80)

        misc_form.addRow("Gamble items:", self._gamble_items)
        misc_form.addRow("Casting frames:", self._casting_frames)
        misc_form.addRow("Max game length:", self._max_game_len)
        misc_form.addRow("Max consecutive fails:", self._max_fails)
        layout.addWidget(misc_box)

        layout.addStretch()

        # Wire signals
        bool_pairs = [
            (self._tog_open_chests,  "char", "open_chests"),
            (self._tog_pre_buff,     "char", "pre_buff_every_run"),
            (self._tog_no_pickup,    "char", "enable_no_pickup"),
            (self._tog_safer,        "char", "safer_routines"),
            (self._tog_fill_shared,  "char", "fill_shared_stash_first"),
            (self._tog_stash_gold,   "char", "stash_gold"),
            (self._tog_sell_junk,    "char", "sell_junk"),
        ]
        for tog, sec, key in bool_pairs:
            tog.toggled_changed.connect(lambda v, s=sec, k=key: get_bridge().set_bool(s, k, v))

        self._gamble_items.textChanged.connect(lambda v: get_bridge().set("char", "gamble_items", v))
        self._casting_frames.valueChanged.connect(lambda v: get_bridge().set("char", "casting_frames", v))
        self._max_game_len.valueChanged.connect(lambda v: get_bridge().set("general", "max_game_length_s", v))
        self._max_fails.valueChanged.connect(lambda v: get_bridge().set("general", "max_consecutive_fails", v))

    def _load_values(self):
        cfg = get_bridge()
        self._tog_open_chests.setChecked(cfg.get_bool("char", "open_chests", True))
        self._tog_pre_buff.setChecked(cfg.get_bool("char", "pre_buff_every_run", True))
        self._tog_no_pickup.setChecked(cfg.get_bool("char", "enable_no_pickup", True))
        self._tog_safer.setChecked(cfg.get_bool("char", "safer_routines", False))
        self._tog_fill_shared.setChecked(cfg.get_bool("char", "fill_shared_stash_first", False))
        self._tog_stash_gold.setChecked(cfg.get_bool("char", "stash_gold", True))
        self._tog_sell_junk.setChecked(cfg.get_bool("char", "sell_junk", False))
        self._gamble_items.setText(cfg.get("char", "gamble_items", ""))
        self._casting_frames.setValue(cfg.get_int("char", "casting_frames", 10))
        self._max_game_len.setValue(cfg.get_int("general", "max_game_length_s", 380))
        self._max_fails.setValue(cfg.get_int("general", "max_consecutive_fails", 5))
