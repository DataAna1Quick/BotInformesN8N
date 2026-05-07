"""Tab 2 — edit the default palette JSON with colour pickers and a live preview."""
from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QColorDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from .. import paths


EDITABLE_KEYS = [
    ("client_default", "primary",  "Color primario cliente (default)"),
    ("client_default", "accent",   "Acento (compartido)"),
    ("provider",       "primary",  "Amarillo Quick Help"),
    ("provider",       "dark",     "Negro Quick Help"),
    ("system",         "success",  "Verde (cumplimiento)"),
    ("system",         "alert",    "Rojo (alerta)"),
]


def _parse_hex(s: str) -> str:
    s = s.strip().upper()
    if not s.startswith("#"):
        s = "#" + s
    if len(s) != 7:
        return "#000000"
    return s


class ColorRow(QWidget):
    def __init__(self, label: str, hex_value: str, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)

        self.swatch = QFrame()
        self.swatch.setFixedSize(32, 24)
        self.swatch.setFrameShape(QFrame.Shape.Box)
        h.addWidget(self.swatch)

        self.value_label = QLabel(hex_value)
        self.value_label.setMinimumWidth(80)
        h.addWidget(self.value_label)

        self.btn = QPushButton("Cambiar…")
        self.btn.clicked.connect(self._pick)
        h.addWidget(self.btn)
        h.addStretch(1)

        self._set(hex_value)

    def _set(self, hex_value: str):
        self.hex_value = _parse_hex(hex_value)
        self.value_label.setText(self.hex_value)
        pal = self.swatch.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self.hex_value))
        self.swatch.setAutoFillBackground(True)
        self.swatch.setPalette(pal)

    def _pick(self):
        c = QColorDialog.getColor(QColor(self.hex_value), self, "Selecciona color")
        if c.isValid():
            self._set(c.name())

    def value(self) -> str:
        return self.hex_value


class PaletteEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: dict[tuple[str, str], ColorRow] = {}
        self._raw: dict = {}
        self._build()
        self._reload()

    def _build(self):
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "Paleta default. El color del cliente se sobreescribe automáticamente "
            "en cada generación con la extracción del logo. Aquí editas los valores "
            "fijos (Quick Help) y los defaults de fallback."
        ))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        for section, key, label in EDITABLE_KEYS:
            row = ColorRow(label, "#000000")
            self._rows[(section, key)] = row
            form.addRow(label, row)
        v.addLayout(form)

        v.addStretch(1)
        bar = QHBoxLayout()
        self.status = QLabel("")
        bar.addWidget(self.status, 1)
        b1 = QPushButton("Recargar desde disco")
        b1.clicked.connect(self._reload)
        bar.addWidget(b1)
        b2 = QPushButton("Guardar")
        b2.setDefault(True)
        b2.clicked.connect(self._save)
        bar.addWidget(b2)
        v.addLayout(bar)

    def _reload(self):
        if not paths.PALETTE_FILE.exists():
            QMessageBox.warning(self, "Archivo no encontrado",
                                f"{paths.PALETTE_FILE} no existe.")
            return
        self._raw = json.loads(paths.PALETTE_FILE.read_text(encoding="utf-8"))
        for (section, key), row in self._rows.items():
            value = self._raw.get(section, {}).get(key, "#000000")
            row._set(value)
        self.status.setText(f"Cargado · {paths.PALETTE_FILE.name}")

    def _save(self):
        for (section, key), row in self._rows.items():
            self._raw.setdefault(section, {})[key] = row.value()
        try:
            paths.PALETTE_FILE.write_text(
                json.dumps(self._raw, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.status.setText(f"Guardado · {paths.PALETTE_FILE.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")
