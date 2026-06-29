"""
Attack Lengths page — atk_len_* settings per boss/run.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QDoubleSpinBox, QScrollArea
)
from launcher.config_bridge import get_bridge


ATK_FIELDS = [
    ("atk_len_pindle",          "Pindle"),
    ("atk_len_eldritch",        "Eldritch"),
    ("atk_len_shenk",           "Shenk"),
    ("atk_len_trav",            "Travincal"),
    ("atk_len_nihlathak",       "Nihlathak"),
    ("atk_len_arc",             "Arcane Sanctuary"),
    ("atk_len_diablo",          "Diablo"),
    ("atk_len_diablo_vizier",   "Diablo — Vizier"),
    ("atk_len_diablo_deseis",   "Diablo — De Seis"),
    ("atk_len_diablo_infector", "Diablo — Infector"),
    ("atk_len_cs_trashmobs",    "CS Trash Mobs"),
]


class AttackLengthsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets: dict[str, QDoubleSpinBox] = {}
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
            "Attack length (seconds) controls how long Botty attacks each target. "
            "Higher values are safer but slower. Barbarians typically need 8–12."
        )
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        box = QGroupBox("Attack lengths (seconds)")
        form = QFormLayout(box)
        form.setSpacing(8)
        form.setContentsMargins(12, 16, 12, 12)

        for key, label in ATK_FIELDS:
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 30.0)
            spin.setSingleStep(0.5)
            spin.setDecimals(1)
            spin.setMaximumWidth(100)
            form.addRow(f"{label}:", spin)
            self._widgets[key] = spin
            spin.valueChanged.connect(lambda v, k=key: get_bridge().set("char", k, v))

        layout.addWidget(box)
        layout.addStretch()

    def _load_values(self):
        cfg = get_bridge()
        defaults = {
            "atk_len_pindle": 3.0, "atk_len_eldritch": 3.0, "atk_len_shenk": 4.0,
            "atk_len_trav": 3.0, "atk_len_nihlathak": 4.0, "atk_len_arc": 2.5,
            "atk_len_diablo": 3.0, "atk_len_diablo_vizier": 2.0,
            "atk_len_diablo_deseis": 5.0, "atk_len_diablo_infector": 4.0,
            "atk_len_cs_trashmobs": 1.5,
        }
        for key, spin in self._widgets.items():
            spin.setValue(cfg.get_float("char", key, defaults.get(key, 3.0)))
