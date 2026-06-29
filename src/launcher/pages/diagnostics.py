"""
Diagnostics page — log viewer and run statistics.
"""
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QSplitter, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOG_DIR = _PROJECT_ROOT / "log"


class DiagnosticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_file: Path | None = None
        self._last_pos = 0
        self._build_ui()
        self._auto_select_log()

        # Poll log every 2 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tail_log)
        self._timer.start(2000)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────
        banner = QLabel("View live bot logs and session diagnostics.")
        banner.setObjectName("info_banner")
        banner.setWordWrap(True)
        root.addWidget(banner)

        # ── Log viewer ────────────────────────────────────────────────
        log_box = QGroupBox("Bot Log")
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(8, 12, 8, 8)
        log_layout.setSpacing(6)

        ctrl_row = QHBoxLayout()
        self._lbl_file = QLabel("No log file selected")
        self._lbl_file.setStyleSheet("color:#888; font-size:12px;")
        btn_open = QPushButton("Open file…")
        btn_open.setObjectName("btn_secondary")
        btn_open.setFixedWidth(90)
        btn_open.clicked.connect(self._open_log)
        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("btn_secondary")
        btn_clear.setFixedWidth(60)
        btn_clear.clicked.connect(self._clear_log)
        ctrl_row.addWidget(self._lbl_file, stretch=1)
        ctrl_row.addWidget(btn_open)
        ctrl_row.addWidget(btn_clear)
        log_layout.addLayout(ctrl_row)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        font = QFont("Consolas", 10)
        self._log_view.setFont(font)
        self._log_view.setStyleSheet(
            "background:#1e1e1e; color:#d4d4d4; border:none; border-radius:3px; padding:6px;"
        )
        self._log_view.setMinimumHeight(320)
        log_layout.addWidget(self._log_view)
        root.addWidget(log_box, stretch=1)

        # ── Stats ─────────────────────────────────────────────────────
        stats_box = QGroupBox("Session stats")
        stats_layout = QHBoxLayout(stats_box)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(24)

        for label in ["Games played: —", "Items found: —", "Chickens: —", "Uptime: —"]:
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size:13px;")
            stats_layout.addWidget(lbl)
        stats_layout.addStretch()
        root.addWidget(stats_box)

    def _auto_select_log(self):
        """Pick the most recent log file from the log/ directory."""
        if not _LOG_DIR.exists():
            return
        logs = sorted(_LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            self._set_log(logs[0])

    def _open_log(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open log file", str(_LOG_DIR), "Log files (*.log *.txt);;All files (*)"
        )
        if path:
            self._set_log(Path(path))

    def _set_log(self, path: Path):
        self._log_file = path
        self._last_pos = 0
        self._lbl_file.setText(path.name)
        self._log_view.clear()
        self._tail_log()

    def _tail_log(self):
        if self._log_file is None or not self._log_file.exists():
            return
        try:
            with open(self._log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._last_pos)
                new_text = f.read()
                self._last_pos = f.tell()
            if new_text:
                # Colour code lines
                for line in new_text.splitlines(keepends=True):
                    ll = line.lower()
                    if "error" in ll or "exception" in ll:
                        color = "#f48771"
                    elif "warning" in ll or "warn" in ll:
                        color = "#cca700"
                    elif "info" in ll:
                        color = "#9cdcfe"
                    else:
                        color = "#d4d4d4"
                    self._log_view.setTextColor(QColor(color))
                    self._log_view.insertPlainText(line)

                # Scroll to bottom
                self._log_view.moveCursor(QTextCursor.MoveOperation.End)
        except Exception:
            pass

    def _clear_log(self):
        self._log_view.clear()
        self._last_pos = 0
