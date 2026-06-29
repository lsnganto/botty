"""
Transmute page.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QSpinBox, QLineEdit, QScrollArea, QCheckBox, QHBoxLayout
)
from launcher.config_bridge import get_bridge


GEMS = ["chipped", "flawed", "standard", "flawless"]


class TransmutePage(QWidget):
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

        banner = QLabel("Configure which gems to transmute and how often.")
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        box = QGroupBox("Transmute settings")
        form = QFormLayout(box)
        form.setSpacing(8)
        form.setContentsMargins(12, 16, 12, 12)

        self._freq = QSpinBox()
        self._freq.setRange(1, 500)
        self._freq.setSuffix(" games")
        self._freq.setMaximumWidth(140)
        form.addRow("Transmute every:", self._freq)

        self._stash_dest = QLineEdit()
        self._stash_dest.setPlaceholderText("e.g. 3,2,1,0")
        self._stash_dest.setMaximumWidth(160)
        form.addRow("Stash destination priority:", self._stash_dest)

        layout.addWidget(box)

        gem_box = QGroupBox("Gems to transmute")
        gem_layout = QHBoxLayout(gem_box)
        gem_layout.setContentsMargins(12, 16, 12, 12)
        gem_layout.setSpacing(16)

        self._gem_checks: dict[str, QCheckBox] = {}
        for gem in GEMS:
            cb = QCheckBox(gem.capitalize())
            gem_layout.addWidget(cb)
            self._gem_checks[gem] = cb
            cb.stateChanged.connect(self._on_gem_change)

        gem_layout.addStretch()
        layout.addWidget(gem_box)
        layout.addStretch()

        self._freq.valueChanged.connect(
            lambda v: get_bridge().set("transmute", "transmute_every_x_game", v)
        )
        self._stash_dest.textChanged.connect(
            lambda v: get_bridge().set("transmute", "stash_destination", v)
        )

    def _on_gem_change(self):
        selected = [g for g, cb in self._gem_checks.items() if cb.isChecked()]
        get_bridge().set_list("transmute", "transmute", selected)

    def _load_values(self):
        cfg = get_bridge()
        self._freq.setValue(cfg.get_int("transmute", "transmute_every_x_game", 20))
        self._stash_dest.setText(cfg.get("transmute", "stash_destination", "3,2,1,0"))
        selected = cfg.get_list("transmute", "transmute")
        for gem, cb in self._gem_checks.items():
            cb.setChecked(gem in selected)
