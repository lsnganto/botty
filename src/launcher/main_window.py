"""
MainWindow — the top-level window of the Botty GUI launcher.

Layout:
  ┌──────────┬──────────────────────────────────────────┐
  │ Sidebar  │  Top bar (Save / Cancel / Wizard / Status)│
  │          ├──────────────────────────────────────────┤
  │  nav     │  QStackedWidget (one page per nav item)   │
  │  links   │                                           │
  │          │                                           │
  │──────────│                                           │
  │ Loot /   │                                           │
  │ Diag     │                                           │
  └──────────┴──────────────────────────────────────────┘
  │  Status bar (● Stopped / Running / Paused)           │
  └──────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QSizePolicy, QSpacerItem, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QIcon, QFont

from launcher.config_bridge import get_bridge, reset_bridge
from launcher.pages import (
    RunProfilePage, ClassSkillsPage, BeltInventoryPage,
    PotionsHealthPage, AttackLengthsPage, MiscPage,
    TransmutePage, DiscordPage, GameSettingsPage,
    LootPickitPage, DiagnosticsPage,
)

# ── Nav item definitions ────────────────────────────────────────────────
_NAV_ITEMS = [
    # (label, page_class | None for separator)
    ("Run profile",      RunProfilePage),
    ("Class & Skills",   ClassSkillsPage),
    ("Belt & Inventory", BeltInventoryPage),
    ("Potions & Health", PotionsHealthPage),
    ("Attack lengths",   AttackLengthsPage),
    ("Misc",             MiscPage),
    ("Transmute",        TransmutePage),
    ("Discord",          DiscordPage),
    ("Game Settings",    GameSettingsPage),
    (None, None),  # visual separator
    ("Loot / Pickit",    LootPickitPage),
    ("Diagnostics",      DiagnosticsPage),
]


class BotRunnerSignals(QObject):
    status_changed = pyqtSignal(str)  # "stopped" | "running" | "paused"


class MainWindow(QMainWindow):
    def __init__(self, game_controller=None, parent=None):
        super().__init__(parent)
        self._game_controller = game_controller
        self._nav_buttons: list[tuple[QPushButton, int]] = []  # (button, stack_index)
        self._current_page = 0
        self._bot_status = "stopped"

        self.setWindowTitle("Botty Client Launcher")
        self.setMinimumSize(QSize(900, 620))
        self.resize(1020, 680)

        self._load_stylesheet()
        self._build_ui()
        self._select_nav(0)

    # ------------------------------------------------------------------ #
    #  Stylesheet                                                          #
    # ------------------------------------------------------------------ #
    def _load_stylesheet(self):
        qss_path = Path(__file__).parent / "style.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────
        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        # ── Right side ────────────────────────────────────────────────
        right_wrapper = QWidget()
        right_layout  = QVBoxLayout(right_wrapper)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top bar
        top_bar = self._build_top_bar()
        right_layout.addWidget(top_bar)

        # Page stack
        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")
        self._populate_stack()
        right_layout.addWidget(self._stack, stretch=1)

        # Status bar
        status_bar = self._build_status_bar()
        right_layout.addWidget(status_bar)

        root.addWidget(right_wrapper, stretch=1)

    # ── Sidebar ─────────────────────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        layout  = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # BOTTY title
        title = QLabel("BOTTY")
        title.setObjectName("sidebar_title")
        layout.addWidget(title)

        # Run button (big)
        run_btn = QPushButton("▶  Run")
        run_btn.setObjectName("nav_button")
        run_btn.setStyleSheet(
            "QPushButton#nav_button { font-weight: 600; padding: 10px 16px; "
            "color: #0098c9; font-size: 14px; }"
            "QPushButton#nav_button:hover { background: #e8f4f8; }"
        )
        run_btn.clicked.connect(self._toggle_run)
        layout.addWidget(run_btn)
        self._run_nav_btn = run_btn

        # Separator
        sep = QFrame()
        sep.setObjectName("sidebar_separator")
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #d0d0d0; margin: 4px 12px;")
        layout.addWidget(sep)

        # Nav items
        stack_idx = 0
        for label, page_cls in _NAV_ITEMS:
            if label is None:
                # Visual separator
                spacer_sep = QFrame()
                spacer_sep.setFixedHeight(1)
                spacer_sep.setStyleSheet("background-color: #d0d0d0; margin: 4px 12px;")
                layout.addWidget(spacer_sep)
                continue

            btn = QPushButton(label)
            btn.setObjectName("nav_button")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked, idx=stack_idx: self._select_nav(idx))
            layout.addWidget(btn)
            self._nav_buttons.append((btn, stack_idx))
            stack_idx += 1

        layout.addStretch()

        # License link
        lic_btn = QPushButton("License")
        lic_btn.setObjectName("license_link")
        lic_btn.setFlat(True)
        lic_btn.setStyleSheet(
            "QPushButton { color:#888; font-size:12px; border:none; padding:6px 16px; "
            "text-align:left; background:transparent; }"
            "QPushButton:hover { color:#0098c9; }"
        )
        layout.addWidget(lic_btn)

        sidebar.setFixedWidth(168)
        return sidebar

    # ── Top bar ─────────────────────────────────────────────────────────
    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("top_bar")
        bar.setFixedHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)

        self._btn_save   = QPushButton("Save")
        self._btn_cancel = QPushButton("Cancel")
        self._btn_save.setObjectName("btn_save")
        self._btn_cancel.setObjectName("btn_cancel")
        self._btn_save.setEnabled(False)
        self._btn_cancel.setEnabled(False)
        self._btn_save.clicked.connect(self._save_config)
        self._btn_cancel.clicked.connect(self._discard_config)

        btn_wizard = QPushButton("Setup wizard")
        btn_wizard.setObjectName("btn_wizard")

        self._changes_label = QLabel("No changes")
        self._changes_label.setObjectName("changes_label")

        layout.addWidget(self._btn_save)
        layout.addWidget(self._btn_cancel)
        layout.addWidget(btn_wizard)
        layout.addWidget(self._changes_label)
        layout.addStretch()

        # License on far right
        lic = QPushButton("License")
        lic.setObjectName("license_link")
        lic.setFlat(True)
        lic.setStyleSheet(
            "QPushButton { color:#444; font-size:13px; border:none; background:transparent; }"
            "QPushButton:hover { color:#0098c9; }"
        )
        layout.addWidget(lic)

        return bar

    # ── Status bar ──────────────────────────────────────────────────────
    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("status_bar")
        bar.setFixedHeight(30)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        self._status_dot   = QLabel("●")
        self._status_label = QLabel("Stopped")
        self._status_dot.setObjectName("status_dot_stopped")
        self._status_dot.setStyleSheet("color:#888;")
        layout.addWidget(self._status_dot)
        layout.addWidget(self._status_label)
        layout.addStretch()

        return bar

    # ── Page stack ──────────────────────────────────────────────────────
    def _populate_stack(self):
        """Lazily instantiate and add all pages to the QStackedWidget."""
        page_classes = [cls for label, cls in _NAV_ITEMS if cls is not None]
        self._pages: list[QWidget | None] = [None] * len(page_classes)
        self._page_classes = page_classes

        # Add placeholder widgets now — actual pages created on first visit
        for _ in page_classes:
            placeholder = QWidget()
            self._stack.addWidget(placeholder)

    def _ensure_page(self, idx: int):
        """Create the page widget if it hasn't been created yet (lazy)."""
        if self._pages[idx] is None:
            page = self._page_classes[idx]()
            self._pages[idx] = page
            # Replace placeholder with real page
            placeholder = self._stack.widget(idx)
            self._stack.insertWidget(idx, page)
            self._stack.removeWidget(placeholder)
            placeholder.deleteLater()

    # ------------------------------------------------------------------ #
    #  Navigation                                                          #
    # ------------------------------------------------------------------ #
    def _select_nav(self, idx: int):
        self._current_page = idx
        self._ensure_page(idx)
        self._stack.setCurrentIndex(idx)

        for btn, btn_idx in self._nav_buttons:
            is_active = (btn_idx == idx)
            btn.setProperty("active", "true" if is_active else "false")
            # Force style refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ------------------------------------------------------------------ #
    #  Config save / discard                                               #
    # ------------------------------------------------------------------ #
    def _on_config_changed(self):
        has_changes = get_bridge().has_changes
        self._btn_save.setEnabled(has_changes)
        self._btn_cancel.setEnabled(has_changes)
        self._changes_label.setText(
            "Unsaved changes" if has_changes else "No changes"
        )
        self._changes_label.setStyleSheet(
            "color: #e07000;" if has_changes else "color: #00a651;"
        )

    def _save_config(self):
        get_bridge().save()
        self._on_config_changed()

    def _discard_config(self):
        get_bridge().discard()
        reset_bridge()
        # Reload all instantiated pages
        for i, page in enumerate(self._pages):
            if page is not None:
                self._pages[i] = None
                placeholder = QWidget()
                self._stack.insertWidget(i, placeholder)
                self._stack.removeWidget(page)
                page.deleteLater()
        self._select_nav(self._current_page)
        self._on_config_changed()

    # ------------------------------------------------------------------ #
    #  Bot Run / Stop                                                      #
    # ------------------------------------------------------------------ #
    def _toggle_run(self):
        if self._bot_status == "stopped":
            self._start_bot()
        elif self._bot_status == "running":
            self._pause_bot()
        elif self._bot_status == "paused":
            self._resume_bot()

    def _start_bot(self):
        if self._game_controller:
            self._game_controller.start()
        self._set_status("running")

    def _pause_bot(self):
        if self._game_controller:
            self._game_controller.toggle_pause_bot()
        self._set_status("paused")

    def _resume_bot(self):
        if self._game_controller:
            self._game_controller.toggle_pause_bot()
        self._set_status("running")

    def _set_status(self, status: str):
        self._bot_status = status
        colors = {
            "stopped": ("#888888", "Stopped",  "▶  Run"),
            "running": ("#00a651", "Running",  "⏸  Pause"),
            "paused":  ("#f0a500", "Paused",   "▶  Resume"),
        }
        color, label, run_text = colors[status]
        self._status_dot.setStyleSheet(f"color: {color};")
        self._status_label.setText(label)
        self._run_nav_btn.setText(run_text)

    # ------------------------------------------------------------------ #
    #  Close                                                               #
    # ------------------------------------------------------------------ #
    def closeEvent(self, event):
        if get_bridge().has_changes:
            # Could prompt to save — for now just discard
            get_bridge().discard()
        if self._game_controller and self._game_controller.is_running:
            self._game_controller.stop()
        super().closeEvent(event)
