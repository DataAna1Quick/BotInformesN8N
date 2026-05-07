"""Tab 3 — toggle slides on/off, reorder by drag, edit slide titles."""
from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import paths


COLS = ["Activo", "Orden", "ID", "Título"]


class SlidesEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw: dict = {}
        self._build()
        self._reload()

    def _build(self):
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "Activa o desactiva slides, cambia el orden (arrastra filas) "
            "y edita los títulos default. Persistido en assets/slides_config.json."
        ))

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.table.setDragDropOverwriteMode(False)
        self.table.verticalHeader().setVisible(False)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.table, 1)

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
        if not paths.SLIDES_FILE.exists():
            QMessageBox.warning(self, "Archivo no encontrado",
                                f"{paths.SLIDES_FILE} no existe.")
            return
        self._raw = json.loads(paths.SLIDES_FILE.read_text(encoding="utf-8"))
        slides = sorted(self._raw.get("slides", []), key=lambda s: s.get("order", 999))
        self.table.setRowCount(len(slides))
        for r, s in enumerate(slides):
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.CheckState.Checked if s.get("enabled", True)
                              else Qt.CheckState.Unchecked)
            chk.setFlags(chk.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setFlags(chk.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 0, chk)

            order_it = QTableWidgetItem(str(s.get("order", r + 1)))
            order_it.setFlags(order_it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 1, order_it)

            id_it = QTableWidgetItem(s.get("id", ""))
            id_it.setFlags(id_it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 2, id_it)

            title_it = QTableWidgetItem(s.get("title", ""))
            self.table.setItem(r, 3, title_it)
        self.status.setText(f"Cargado · {paths.SLIDES_FILE.name}")

    def _save(self):
        new_slides = []
        for r in range(self.table.rowCount()):
            enabled = self.table.item(r, 0).checkState() == Qt.CheckState.Checked
            sid = self.table.item(r, 2).text()
            title = self.table.item(r, 3).text()
            new_slides.append({
                "id": sid, "enabled": enabled,
                "order": r + 1, "title": title,
            })
        self._raw["slides"] = new_slides
        try:
            paths.SLIDES_FILE.write_text(
                json.dumps(self._raw, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.status.setText(f"Guardado · {paths.SLIDES_FILE.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")
