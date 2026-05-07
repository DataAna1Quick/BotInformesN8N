"""BotInformesN8N · Dev Console (PyQt6).

Lanzada por run_dev_console.bat.
Permite al equipo Quick Help editar prompts, paleta, slides, ver consumo de API
y correr el pipeline localmente — sin tocar código.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QStatusBar,
    QTabWidget, QVBoxLayout, QWidget,
)

# Make `core` importable from any module
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "streamlit_app"))

from dev_console.modules.api_monitor import ApiMonitor
from dev_console.modules.palette_editor import PaletteEditor
from dev_console.modules.prompt_editor import PromptEditor
from dev_console.modules.slides_editor import SlidesEditor
from dev_console.modules.test_runner import TestRunner


LOGO_PATH = ROOT / "streamlit_app" / "assets" / "logo_quick.png"


STYLE = """
QMainWindow, QWidget { background: #F7F8FB; color: #0F1419; }
QLabel { color: #0F1419; }
QPushButton {
    background: #1B3D7A; color: white; border: 0; padding: 6px 14px;
    border-radius: 4px; font-weight: 600;
}
QPushButton:hover { background: #2A56A6; }
QPushButton:disabled { background: #B0B6C2; color: #F7F8FB; }
QPushButton:default { background: #F4B400; color: #0F1419; }
QPushButton:default:hover { background: #FFC833; }
QLineEdit, QPlainTextEdit, QTableWidget {
    background: #FFFFFF; border: 1px solid #E6E8EE; border-radius: 4px;
    padding: 6px; selection-background-color: #1B3D7A;
}
QTabWidget::pane { border: 1px solid #E6E8EE; background: #FFFFFF; }
QTabBar::tab {
    background: #E6E8EE; padding: 8px 16px; margin-right: 2px;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
    color: #3F4452; font-weight: 600;
}
QTabBar::tab:selected { background: #FFFFFF; color: #1B3D7A; border-bottom: 2px solid #F4B400; }
QHeaderView::section {
    background: #1B3D7A; color: white; padding: 6px; border: 0; font-weight: 600;
}
QStatusBar { background: #1B3D7A; color: white; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BotInformesN8N · Dev Console")
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.resize(1100, 720)

        # Header
        header = QWidget()
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 8, 12, 8)
        if LOGO_PATH.exists():
            logo = QLabel()
            pix = QPixmap(str(LOGO_PATH)).scaledToHeight(36,
                                                         Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pix)
            h.addWidget(logo)
        title = QLabel("<b>BotInformesN8N</b> · Consola de desarrollo")
        title.setStyleSheet("color:#1B3D7A; font-size:16px;")
        h.addWidget(title)
        h.addStretch(1)
        version = QLabel("v0.1.0")
        version.setStyleSheet("color:#7A7F8C;")
        h.addWidget(version)
        header.setStyleSheet("background:#FFFFFF; border-bottom:2px solid #F4B400;")

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(PromptEditor(),  "Prompts")
        self.tabs.addTab(PaletteEditor(), "Paleta")
        self.tabs.addTab(SlidesEditor(),  "Slides")
        self.tabs.addTab(ApiMonitor(),    "API Monitor")
        self.tabs.addTab(TestRunner(),    "Test runner")

        # Central layout
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(header)
        v.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        # Status bar
        bar = QStatusBar()
        bar.showMessage("Listo · Quick Help SAS · Operaciones y Analítica")
        self.setStatusBar(bar)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
