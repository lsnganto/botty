"""
Discord / Messaging page.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QScrollArea
)
from launcher.config_bridge import get_bridge
from launcher.widgets.toggle_switch import ToggleSwitch


class DiscordPage(QWidget):
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
            "Configure Discord (or custom webhook) notifications. "
            "Leave webhooks blank to disable messaging."
        )
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        box = QGroupBox("Messaging")
        form = QFormLayout(box)
        form.setSpacing(8)
        form.setContentsMargins(12, 16, 12, 12)

        self._api_type = QComboBox()
        self._api_type.addItems(["discord", "custom"])
        self._api_type.setMaximumWidth(160)

        self._loot_hook = QLineEdit()
        self._loot_hook.setPlaceholderText("Discord loot webhook URL")

        self._msg_hook = QLineEdit()
        self._msg_hook.setPlaceholderText("Discord status webhook URL")

        self._status_count = QSpinBox()
        self._status_count.setRange(0, 500)
        self._status_count.setMaximumWidth(100)

        self._tog_log_chicken = ToggleSwitch()

        form.addRow("API type:", self._api_type)
        form.addRow("Loot webhook:", self._loot_hook)
        form.addRow("Status webhook:", self._msg_hook)
        form.addRow("Status every N runs:", self._status_count)
        form.addRow("Log chicken events:", self._tog_log_chicken)
        layout.addWidget(box)
        layout.addStretch()

        self._api_type.currentTextChanged.connect(
            lambda v: get_bridge().set("general", "message_api_type", v)
        )
        self._loot_hook.textChanged.connect(
            lambda v: get_bridge().set("general", "custom_loot_message_hook", v)
        )
        self._msg_hook.textChanged.connect(
            lambda v: get_bridge().set("general", "custom_message_hook", v)
        )
        self._status_count.valueChanged.connect(
            lambda v: get_bridge().set("general", "discord_status_count", v)
        )
        self._tog_log_chicken.toggled_changed.connect(
            lambda v: get_bridge().set_bool("general", "discord_log_chicken", v)
        )

    def _load_values(self):
        cfg = get_bridge()
        idx = self._api_type.findText(cfg.get("general", "message_api_type", "discord"))
        if idx >= 0:
            self._api_type.setCurrentIndex(idx)
        self._loot_hook.setText(cfg.get("general", "custom_loot_message_hook", ""))
        self._msg_hook.setText(cfg.get("general", "custom_message_hook", ""))
        self._status_count.setValue(cfg.get_int("general", "discord_status_count", 20))
        self._tog_log_chicken.setChecked(cfg.get_bool("general", "discord_log_chicken", True))
