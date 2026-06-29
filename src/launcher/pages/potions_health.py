"""
Potions & Health page — thresholds for potion usage and chicken.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QDoubleSpinBox, QScrollArea, QSlider, QHBoxLayout
)
from PyQt6.QtCore import Qt
from launcher.config_bridge import get_bridge


class PotionsHealthPage(QWidget):
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

        banner = QLabel(
            "Set health/mana thresholds (0.0–1.0) at which potions are consumed. "
            "Chicken threshold = HP % at which the bot exits the game."
        )
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        # ── Character ──────────────────────────────────────────────────
        char_box = QGroupBox("Character")
        char_form = QFormLayout(char_box)
        char_form.setSpacing(8)
        char_form.setContentsMargins(12, 16, 12, 12)

        self._take_hp   = self._dspin()
        self._take_mp   = self._dspin()
        self._take_rj_hp= self._dspin()
        self._take_rj_mp= self._dspin()
        self._chicken   = self._dspin()

        char_form.addRow("Drink HP potion below:", self._take_hp)
        char_form.addRow("Drink MP potion below:", self._take_mp)
        char_form.addRow("Drink Rejuv (HP) below:", self._take_rj_hp)
        char_form.addRow("Drink Rejuv (MP) below:", self._take_rj_mp)
        char_form.addRow("Chicken at HP below:", self._chicken)
        layout.addWidget(char_box)

        # ── Mercenary ─────────────────────────────────────────────────
        merc_box = QGroupBox("Mercenary")
        merc_form = QFormLayout(merc_box)
        merc_form.setSpacing(8)
        merc_form.setContentsMargins(12, 16, 12, 12)

        self._heal_merc      = self._dspin()
        self._heal_rejuv_merc= self._dspin()
        self._merc_chicken   = self._dspin()

        merc_form.addRow("Heal merc below HP:", self._heal_merc)
        merc_form.addRow("Rejuv merc below HP:", self._heal_rejuv_merc)
        merc_form.addRow("Chicken (merc) at HP:", self._merc_chicken)
        layout.addWidget(merc_box)

        layout.addStretch()

        # Wire signals
        pairs = [
            (self._take_hp,    "char", "take_health_potion"),
            (self._take_mp,    "char", "take_mana_potion"),
            (self._take_rj_hp, "char", "take_rejuv_potion_health"),
            (self._take_rj_mp, "char", "take_rejuv_potion_mana"),
            (self._chicken,    "char", "chicken"),
            (self._heal_merc,      "char", "heal_merc"),
            (self._heal_rejuv_merc,"char", "heal_rejuv_merc"),
            (self._merc_chicken,   "char", "merc_chicken"),
        ]
        for widget, section, key in pairs:
            widget.valueChanged.connect(lambda v, s=section, k=key: get_bridge().set(s, k, v))

    def _dspin(self) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(0.0, 1.0)
        s.setSingleStep(0.05)
        s.setDecimals(2)
        s.setMaximumWidth(100)
        return s

    def _load_values(self):
        cfg = get_bridge()
        self._take_hp.setValue(cfg.get_float("char", "take_health_potion", 0.8))
        self._take_mp.setValue(cfg.get_float("char", "take_mana_potion", 0.5))
        self._take_rj_hp.setValue(cfg.get_float("char", "take_rejuv_potion_health", 0.4))
        self._take_rj_mp.setValue(cfg.get_float("char", "take_rejuv_potion_mana", 0.1))
        self._chicken.setValue(cfg.get_float("char", "chicken", 0.35))
        self._heal_merc.setValue(cfg.get_float("char", "heal_merc", 0.7))
        self._heal_rejuv_merc.setValue(cfg.get_float("char", "heal_rejuv_merc", 0.2))
        self._merc_chicken.setValue(cfg.get_float("char", "merc_chicken", 0.0))
