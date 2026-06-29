"""
Botty GUI Launcher — QApplication entry point.

Usage:
    python src/launcher/app.py          # standalone
    python src/main.py --gui            # via main entry point
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Ensure src/ is on the path when run directly
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Change working directory to project root so config/ paths resolve correctly
_PROJECT_ROOT = _SRC.parent
os.chdir(str(_PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from launcher.main_window import MainWindow


def run_gui(game_controller=None) -> int:
    """
    Launch the Botty GUI.
    Pass a GameController instance if running inside the full bot stack.
    Returns the QApplication exit code.
    """
    # High-DPI support
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Botty Client Launcher")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Botty")

    # Default font
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    window = MainWindow(game_controller=game_controller)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_gui())
