"""
Game Settings page — d2r path, launch options, anti-detect, breaks.
Mirrors the "Game Settings" node in the Botty Client Launcher sidebar.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QScrollArea,
    QHBoxLayout, QPushButton, QFileDialog
)
from launcher.config_bridge import get_bridge
from launcher.widgets.toggle_switch import ToggleSwitch


class GameSettingsPage(QWidget):
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
            "Configure Diablo II: Resurrected path, launch options, and anti-detect settings."
        )
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        # ── D2R Path ──────────────────────────────────────────────────
        path_box = QGroupBox("Diablo II: Resurrected")
        path_form = QFormLayout(path_box)
        path_form.setSpacing(8)
        path_form.setContentsMargins(12, 16, 12, 12)

        path_row = QHBoxLayout()
        self._d2r_path = QLineEdit()
        self._d2r_path.setPlaceholderText("Path to D2R installation...")
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("btn_secondary")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_d2r)
        path_row.addWidget(self._d2r_path)
        path_row.addWidget(browse_btn)
        path_form.addRow("D2R path:", path_row)

        self._launch_opts = QLineEdit()
        self._launch_opts.setPlaceholderText("-mod <name> -txt")
        path_form.addRow("Launch options:", self._launch_opts)

        self._tog_restart = ToggleSwitch()
        path_form.addRow("Restart D2R when stuck:", self._tog_restart)

        self._char_name = QLineEdit()
        self._char_name.setMaximumWidth(200)
        path_form.addRow("Character name:", self._char_name)

        layout.addWidget(path_box)

        # ── Breaks ────────────────────────────────────────────────────
        break_box = QGroupBox("Session breaks")
        break_form = QFormLayout(break_box)
        break_form.setSpacing(8)
        break_form.setContentsMargins(12, 16, 12, 12)

        self._max_runtime = QDoubleSpinBox()
        self._max_runtime.setRange(0, 24)
        self._max_runtime.setDecimals(1)
        self._max_runtime.setSuffix(" min")
        self._max_runtime.setMaximumWidth(120)
        self._max_runtime.setSpecialValueText("Disabled")

        self._break_len = QDoubleSpinBox()
        self._break_len.setRange(0, 120)
        self._break_len.setDecimals(1)
        self._break_len.setSuffix(" min")
        self._break_len.setMaximumWidth(120)

        break_form.addRow("Max runtime before break:", self._max_runtime)
        break_form.addRow("Break length:", self._break_len)
        layout.addWidget(break_box)

        # ── Anti-Detect ───────────────────────────────────────────────
        anti_box = QGroupBox("Anti-Detect")
        anti_form = QFormLayout(anti_box)
        anti_form.setSpacing(8)
        anti_form.setContentsMargins(12, 16, 12, 12)

        self._tog_anti = ToggleSwitch()
        self._delay_min = QDoubleSpinBox()
        self._delay_min.setRange(0, 300)
        self._delay_min.setSuffix(" s")
        self._delay_min.setMaximumWidth(110)
        self._delay_max = QDoubleSpinBox()
        self._delay_max.setRange(0, 300)
        self._delay_max.setSuffix(" s")
        self._delay_max.setMaximumWidth(110)
        self._max_hours = QDoubleSpinBox()
        self._max_hours.setRange(0, 24)
        self._max_hours.setSuffix(" h/day")
        self._max_hours.setMaximumWidth(120)
        self._jitter = QSpinBox()
        self._jitter.setRange(0, 100)
        self._jitter.setSuffix(" %")
        self._jitter.setMaximumWidth(100)
        self._tog_auto_rand = ToggleSwitch()

        anti_form.addRow("Enabled:", self._tog_anti)
        anti_form.addRow("Between-game delay min:", self._delay_min)
        anti_form.addRow("Between-game delay max:", self._delay_max)
        anti_form.addRow("Max hours per day:", self._max_hours)
        anti_form.addRow("Break jitter (%):", self._jitter)
        anti_form.addRow("Auto-randomize runs:", self._tog_auto_rand)
        layout.addWidget(anti_box)

        layout.addStretch()

        # Wire signals
        self._d2r_path.textChanged.connect(lambda v: get_bridge().set("general", "d2r_path", v))
        self._launch_opts.textChanged.connect(lambda v: get_bridge().set("advanced_options", "launch_options", v))
        self._tog_restart.toggled_changed.connect(lambda v: get_bridge().set_bool("general", "restart_d2r_when_stuck", v))
        self._char_name.textChanged.connect(lambda v: get_bridge().set("general", "name", v))
        self._max_runtime.valueChanged.connect(lambda v: get_bridge().set("general", "max_runtime_before_break_m", v))
        self._break_len.valueChanged.connect(lambda v: get_bridge().set("general", "break_length_m", v))
        self._tog_anti.toggled_changed.connect(lambda v: get_bridge().set_bool("anti_detect", "enabled", v))
        self._delay_min.valueChanged.connect(lambda v: get_bridge().set("anti_detect", "between_game_delay_min", v))
        self._delay_max.valueChanged.connect(lambda v: get_bridge().set("anti_detect", "between_game_delay_max", v))
        self._max_hours.valueChanged.connect(lambda v: get_bridge().set("anti_detect", "max_hours_per_day", v))
        self._jitter.valueChanged.connect(lambda v: get_bridge().set("anti_detect", "break_jitter_pct", v))
        self._tog_auto_rand.toggled_changed.connect(lambda v: get_bridge().set_bool("anti_detect", "auto_randomize", v))

    def _browse_d2r(self):
        folder = QFileDialog.getExistingDirectory(self, "Select D2R Folder", self._d2r_path.text())
        if folder:
            self._d2r_path.setText(folder)

    def _load_values(self):
        cfg = get_bridge()
        self._d2r_path.setText(cfg.get("general", "d2r_path", ""))
        self._launch_opts.setText(cfg.get("advanced_options", "launch_options", "-mod <name> -txt"))
        self._tog_restart.setChecked(cfg.get_bool("general", "restart_d2r_when_stuck", False))
        self._char_name.setText(cfg.get("general", "name", "Sword"))
        self._max_runtime.setValue(cfg.get_float("general", "max_runtime_before_break_m", 0))
        self._break_len.setValue(cfg.get_float("general", "break_length_m", 0))
        self._tog_anti.setChecked(cfg.get_bool("anti_detect", "enabled", True))
        self._delay_min.setValue(cfg.get_float("anti_detect", "between_game_delay_min", 5))
        self._delay_max.setValue(cfg.get_float("anti_detect", "between_game_delay_max", 20))
        self._max_hours.setValue(cfg.get_float("anti_detect", "max_hours_per_day", 3.5))
        self._jitter.setValue(cfg.get_int("anti_detect", "break_jitter_pct", 20))
        self._tog_auto_rand.setChecked(cfg.get_bool("anti_detect", "auto_randomize", True))
