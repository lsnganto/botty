"""
Loot / Pickit Editor — table-based BNIP rule viewer/editor.
Mirrors the third screenshot with category tabs, rule table, and detail panel.
"""
from __future__ import annotations
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QHeaderView,
    QSplitter, QGroupBox, QFormLayout, QCheckBox, QAbstractItemView,
    QButtonGroup, QRadioButton, QFrame, QTabBar, QTabWidget,
    QScrollArea, QSizePolicy, QTextEdit
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QColor, QFont


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BNIP = _PROJECT_ROOT / "config" / "default.bnip"
_CUSTOM_BNIP  = _PROJECT_ROOT / "config" / "bnip"

CATEGORIES = ["Misc", "Runes", "Gems", "Magic Items", "Charms", "Jewelry", "Socket Bases", "Uniques/Sets"]


class LootPickitPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[dict] = []
        self._filtered_rules: list[dict] = []
        self._current_category = "Uniques/Sets"
        self._build_ui()
        self._load_rules()

    # ------------------------------------------------------------------ #
    #  UI                                                                  #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background: #fff; border-bottom: 1px solid #d8d8d8;")
        header.setFixedHeight(60)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        title = QLabel("Loot / Pickit editor")
        title.setStyleSheet("font-weight: 600; font-size: 15px;")
        sub = QLabel("Edit custom pickit rules directly. Save changes to write custom.bnip.")
        sub.setStyleSheet("color: #888; font-size: 12px;")
        header_layout.addWidget(title)
        header_layout.addWidget(sub)
        root.addWidget(header)

        # ── Category tabs ─────────────────────────────────────────────
        self._tab_bar = QTabWidget()
        self._tab_bar.setTabPosition(QTabWidget.TabPosition.North)
        self._tab_bar.setDocumentMode(True)

        # Each tab is a placeholder; we filter the table by tab index
        for cat in CATEGORIES:
            tab_page = QWidget()
            self._tab_bar.addTab(tab_page, cat)

        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tab_bar)

        # ── Main area: splitter (table | detail) ──────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        root.addWidget(splitter, stretch=1)

        # Left: search + table
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 6, 0)
        left_layout.setSpacing(8)

        lbl_rules = QLabel("RULES")
        lbl_rules.setObjectName("section_label")
        left_layout.addWidget(lbl_rules)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search rules...")
        self._search.textChanged.connect(self._apply_filter)
        left_layout.addWidget(self._search)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["On", "Type", "Rule", "Quality", "Threshold"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.currentItemChanged.connect(self._on_row_selected)
        left_layout.addWidget(self._table)

        # Bottom button bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)
        btn_bar.setContentsMargins(0, 8, 0, 8)

        btn_add  = QPushButton("Add rule")
        btn_add.setObjectName("btn_primary")
        btn_dup  = QPushButton("Duplicate")
        btn_dup.setObjectName("btn_secondary")
        btn_del  = QPushButton("Delete")
        btn_del.setObjectName("btn_danger")
        for btn in (btn_add, btn_dup, btn_del):
            btn_bar.addWidget(btn)
        btn_bar.addStretch()
        left_layout.addLayout(btn_bar)

        splitter.addWidget(left)

        # Right: rule detail panel
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(right_scroll.Shape.NoFrame)
        right = QWidget()
        right_scroll.setWidget(right)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        detail_title = QLabel("RULE DETAILS")
        detail_title.setObjectName("section_label")
        right_layout.addWidget(detail_title)

        self._detail_source = QLabel("Loaded from default.bnip")
        self._detail_source.setStyleSheet("color: #888; font-size: 12px;")
        right_layout.addWidget(self._detail_source)

        # Name / type badge row
        name_row = QHBoxLayout()
        self._detail_badge = QLabel("UNIQ")
        self._detail_badge.setStyleSheet(
            "background:#0098c9; color:#fff; border-radius:3px; padding:2px 6px; font-weight:bold; font-size:11px;"
        )
        self._detail_name = QLabel("—")
        self._detail_name.setStyleSheet("font-size:15px; font-weight:600;")
        name_row.addWidget(self._detail_badge)
        name_row.addWidget(self._detail_name)
        name_row.addStretch()
        right_layout.addLayout(name_row)

        self._detail_sub = QLabel("—")
        self._detail_sub.setStyleSheet("color:#888; font-size:12px;")
        right_layout.addWidget(self._detail_sub)

        # Enabled + Discord
        enab_row = QHBoxLayout()
        self._det_enabled = QCheckBox("Enabled")
        self._det_discord = QCheckBox("Notify Discord")
        self._det_discord.setChecked(True)
        enab_row.addWidget(self._det_enabled)
        enab_row.addWidget(self._det_discord)
        enab_row.addStretch()
        right_layout.addLayout(enab_row)

        btn_add_cond = QPushButton("Add condition")
        btn_add_cond.setObjectName("btn_secondary")
        right_layout.addWidget(btn_add_cond)

        # Affix presets
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e0e0e0;")
        right_layout.addWidget(sep)

        lbl_affix = QLabel("AFFIX / SUFFIX PRESETS")
        lbl_affix.setObjectName("section_label")
        right_layout.addWidget(lbl_affix)

        lbl_flags = QLabel("ITEM FLAGS")
        lbl_flags.setStyleSheet("font-weight:600; color:#555;")
        right_layout.addWidget(lbl_flags)

        eth_row = QHBoxLayout()
        eth_row.addWidget(QLabel("Ethereal"))
        self._eth_any = QPushButton("Any")
        self._eth_yes = QPushButton("Yes")
        self._eth_no  = QPushButton("No")
        for btn in (self._eth_any, self._eth_yes, self._eth_no):
            btn.setCheckable(True)
            btn.setFixedSize(48, 26)
            btn.setStyleSheet(
                "QPushButton { background:#e8e8e8; border:1px solid #ccc; border-radius:3px; font-size:12px; }"
                "QPushButton:checked { background:#0098c9; color:#fff; border-color:#0098c9; }"
            )
        self._eth_any.setChecked(True)
        eth_row.addWidget(self._eth_any)
        eth_row.addWidget(self._eth_yes)
        eth_row.addWidget(self._eth_no)
        eth_row.addStretch()
        right_layout.addLayout(eth_row)

        lbl_stat = QLabel("STAT CONDITIONS")
        lbl_stat.setStyleSheet("font-weight:600; color:#555;")
        right_layout.addWidget(lbl_stat)

        self._stat_display = QLabel("No stat thresholds. Pickup is based on item properties only.")
        self._stat_display.setWordWrap(True)
        self._stat_display.setStyleSheet(
            "background:#f5f5f5; border:1px solid #e0e0e0; border-radius:3px; "
            "padding:8px; color:#666; font-size:12px;"
        )
        right_layout.addWidget(self._stat_display)

        lbl_preview = QLabel("BNIP PREVIEW")
        lbl_preview.setObjectName("section_label")
        right_layout.addWidget(lbl_preview)

        self._bnip_preview = QTextEdit()
        self._bnip_preview.setReadOnly(True)
        self._bnip_preview.setMaximumHeight(80)
        self._bnip_preview.setStyleSheet(
            "background:#f5f5f5; border:1px solid #e0e0e0; font-family:Consolas,monospace; font-size:11px;"
        )
        right_layout.addWidget(self._bnip_preview)

        # Save / Validate buttons
        sv_row = QHBoxLayout()
        sv_row.addStretch()
        self._btn_save_rule = QPushButton("Save")
        self._btn_save_rule.setObjectName("btn_secondary")
        btn_validate = QPushButton("Validate")
        btn_validate.setObjectName("btn_primary")
        sv_row.addWidget(self._btn_save_rule)
        sv_row.addWidget(btn_validate)
        right_layout.addLayout(sv_row)

        right_layout.addStretch()
        splitter.addWidget(right_scroll)
        splitter.setSizes([550, 350])

    # ------------------------------------------------------------------ #
    #  Data                                                                #
    # ------------------------------------------------------------------ #
    def _load_rules(self):
        """Parse default.bnip into a simple list of dicts."""
        self._rules = []
        if not _DEFAULT_BNIP.exists():
            return

        with open(_DEFAULT_BNIP, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                # Very basic parsing: split on # for conditions
                parts = line.split("#")
                name_part = parts[0].strip()
                threshold = parts[1].strip() if len(parts) > 1 else ""

                # Try to extract item type keyword
                qual = ""
                item_type = "MISC"
                for tag in ["UNIQ", "SET", "RARE", "MAGIC", "NORM"]:
                    if f"[Quality] == {tag}" in line.upper() or tag in line:
                        qual = tag
                        if tag in ("UNIQ", "SET"):
                            item_type = "UNIQ"
                        break

                # Extract item name between quotes if present
                name_match = re.search(r'\[Name\]\s*==\s*(\w+)', line)
                display_name = name_match.group(1).replace("_", " ").title() if name_match else name_part[:40]

                cat = self._guess_category(line)

                self._rules.append({
                    "enabled": True,
                    "type": item_type,
                    "name": display_name,
                    "quality": qual,
                    "threshold": threshold[:60],
                    "raw": line,
                    "category": cat,
                })

        self._on_tab_changed(0)

    def _guess_category(self, line: str) -> str:
        line_lower = line.lower()
        if any(k in line_lower for k in ["rune"]):
            return "Runes"
        if any(k in line_lower for k in ["gem", "amethyst", "ruby", "topaz", "sapphire", "emerald", "diamond", "skull"]):
            return "Gems"
        if "charm" in line_lower:
            return "Charms"
        if any(k in line_lower for k in ["ring", "amulet"]):
            return "Jewelry"
        if any(k in line_lower for k in ["[quality] == uniq", "set"]):
            return "Uniques/Sets"
        if "[quality] == magic" in line_lower:
            return "Magic Items"
        if any(k in line_lower for k in ["socket", "[nsock"]):
            return "Socket Bases"
        return "Misc"

    def _on_tab_changed(self, idx: int):
        cat = CATEGORIES[idx] if idx < len(CATEGORIES) else "Misc"
        self._current_category = cat
        self._apply_filter()

    def _apply_filter(self):
        search = self._search.text().lower()
        self._filtered_rules = [
            r for r in self._rules
            if r["category"] == self._current_category
            and (not search or search in r["name"].lower() or search in r["raw"].lower())
        ]
        self._populate_table()

    def _populate_table(self):
        self._table.setRowCount(0)
        for r in self._filtered_rules:
            row = self._table.rowCount()
            self._table.insertRow(row)

            # On checkbox
            cb = QTableWidgetItem()
            cb.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            cb.setCheckState(Qt.CheckState.Checked if r["enabled"] else Qt.CheckState.Unchecked)
            self._table.setItem(row, 0, cb)

            self._table.setItem(row, 1, QTableWidgetItem(r["type"]))
            self._table.setItem(row, 2, QTableWidgetItem(r["name"]))
            self._table.setItem(row, 3, QTableWidgetItem(r["quality"]))
            self._table.setItem(row, 4, QTableWidgetItem(r["threshold"]))

            # Colour threshold column if present
            if r["threshold"]:
                thresh_item = self._table.item(row, 4)
                thresh_item.setForeground(QColor("#f0a500"))

        # Update tab label with count
        idx = CATEGORIES.index(self._current_category)
        self._tab_bar.setTabText(idx, f"{self._current_category}  {len(self._filtered_rules)}")

    def _on_row_selected(self, current, previous):
        if current is None:
            return
        row = current.row()
        if 0 <= row < len(self._filtered_rules):
            r = self._filtered_rules[row]
            self._detail_name.setText(r["name"])
            self._detail_badge.setText(r["type"])
            self._detail_sub.setText(f"{r['category']} · {r['quality']}")
            self._bnip_preview.setText(r["raw"])
            self._det_enabled.setChecked(r["enabled"])
