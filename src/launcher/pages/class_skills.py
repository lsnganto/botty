"""
Class & Skills page — hotkey mappings for each character class.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGroupBox, QScrollArea, QFormLayout, QComboBox
)
from PyQt6.QtCore import Qt
from launcher.config_bridge import get_bridge


SKILL_SECTIONS = {
    "Sorceress (all)": {
        "section": "sorceress",
        "skills": ["energy_shield", "frozen_armor", "static_field", "telekinesis", "thunder_storm"]
    },
    "Lightning Sorc": {
        "section": "light_sorc",
        "skills": ["lightning", "chain_lightning", "frozen_orb"]
    },
    "Blizzard Sorc": {
        "section": "blizz_sorc",
        "skills": ["blizzard", "ice_blast"]
    },
    "Nova Sorc": {
        "section": "nova_sorc",
        "skills": ["nova"]
    },
    "Hydra Sorc": {
        "section": "hydra_sorc",
        "skills": ["hydra", "alt_attack"]
    },
    "Paladin (all)": {
        "section": "paladin",
        "skills": ["holy_shield", "vigor", "cleansing", "redemption"]
    },
    "Hammerdin": {
        "section": "hammerdin",
        "skills": ["blessed_hammer", "concentration"]
    },
    "FoHdin": {
        "section": "fohdin",
        "skills": ["foh", "holy_bolt", "blessed_hammer", "concentration", "conviction"]
    },
    "Trapsin": {
        "section": "trapsin",
        "skills": ["lightning_sentry", "death_sentry", "burst_of_speed", "fade", "shadow_warrior", "skill_left"]
    },
    "Barbarian": {
        "section": "barbarian",
        "skills": ["war_cry", "shout", "find_item", "leap"]
    },
    "Necro (all)": {
        "section": "necro",
        "skills": ["raise_skeleton", "raise_mage", "raise_revive", "corpse_explosion", "amp_dmg", "bone_armor", "clay_golem", "heart_of_wolverine", "skill_left"]
    },
}

CHAR_HOTKEYS = {
    "section": "char",
    "label": "Game Hotkeys",
    "skills": ["force_move", "inventory_screen", "show_items", "show_belt", "stand_still",
               "teleport", "town_portal", "weapon_switch", "battle_orders", "battle_command",
               "potion1", "potion2", "potion3", "potion4"]
}


class ClassSkillsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._inputs: list[tuple[str, str, QLineEdit]] = []  # (section, key, widget)
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

        banner = QLabel("Assign hotkeys for each class skill. Leave blank if not applicable.")
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        # Game Hotkeys group
        self._add_group(layout, CHAR_HOTKEYS["label"], CHAR_HOTKEYS["section"], CHAR_HOTKEYS["skills"])

        # Per-class skill groups
        for group_label, info in SKILL_SECTIONS.items():
            self._add_group(layout, group_label, info["section"], info["skills"])

        layout.addStretch()

    def _add_group(self, parent_layout, title, section, keys):
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setSpacing(8)
        form.setContentsMargins(12, 16, 12, 12)

        for key in keys:
            lbl = QLabel(key.replace("_", " ").title() + ":")
            edit = QLineEdit()
            edit.setPlaceholderText("key")
            edit.setMaximumWidth(120)
            form.addRow(lbl, edit)
            self._inputs.append((section, key, edit))
            edit.textChanged.connect(lambda val, s=section, k=key: get_bridge().set(s, k, val))

        parent_layout.addWidget(box)

    def _load_values(self):
        cfg = get_bridge()
        for section, key, widget in self._inputs:
            widget.setText(cfg.get(section, key, ""))
