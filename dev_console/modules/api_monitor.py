"""Tab 4 — read .api_log.jsonl and show usage / cost."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import paths


COLS = ["Fecha", "Cliente", "Modelo", "Input tok.", "Output tok.",
        "Costo USD", "Fallback", "Razón"]


class ApiMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._reload()

    def _build(self):
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "Resumen de llamadas a Anthropic API y caídas a plantilla. "
            "Origen: dev_console/.api_log.jsonl (no se commitea)."
        ))

        # KPI strip
        kpi_row = QHBoxLayout()
        self.kpi_total = QLabel("—")
        self.kpi_llm = QLabel("—")
        self.kpi_fallback = QLabel("—")
        self.kpi_cost = QLabel("—")
        for w, label in [
            (self.kpi_total, "Llamadas totales"),
            (self.kpi_llm, "Con IA"),
            (self.kpi_fallback, "Fallback a plantilla"),
            (self.kpi_cost, "Costo acumulado (USD)"),
        ]:
            box = QVBoxLayout()
            t = QLabel(label.upper())
            t.setStyleSheet("color:#7A7F8C; font-size:10px; font-weight:bold;")
            w.setStyleSheet("font-size:18px; font-weight:bold; color:#1B3D7A;")
            box.addWidget(t)
            box.addWidget(w)
            holder = QWidget()
            holder.setLayout(box)
            holder.setStyleSheet(
                "background:#FFFFFF; border:1px solid #E6E8EE; border-radius:6px; "
                "padding:8px;"
            )
            kpi_row.addWidget(holder)
        v.addLayout(kpi_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        h = self.table.horizontalHeader()
        for i in range(len(COLS) - 1):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(len(COLS) - 1, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.table, 1)

        bar = QHBoxLayout()
        self.status = QLabel("")
        bar.addWidget(self.status, 1)
        b = QPushButton("Recargar")
        b.clicked.connect(self._reload)
        bar.addWidget(b)
        v.addLayout(bar)

    def _reload(self):
        records = []
        if paths.API_LOG_FILE.exists():
            for line in paths.API_LOG_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue

        total = len(records)
        n_llm = sum(1 for r in records if not r.get("fallback"))
        n_fb = total - n_llm
        cost_total = sum(float(r.get("cost_usd") or 0) for r in records)

        self.kpi_total.setText(str(total))
        self.kpi_llm.setText(str(n_llm))
        self.kpi_fallback.setText(str(n_fb))
        self.kpi_cost.setText(f"{cost_total:.4f}")

        self.table.setRowCount(total)
        for r, rec in enumerate(reversed(records)):
            cells = [
                rec.get("ts", ""),
                rec.get("client", ""),
                rec.get("model") or "—",
                str(rec.get("input_tokens", "")),
                str(rec.get("output_tokens", "")),
                f"{float(rec.get('cost_usd') or 0):.4f}",
                "Sí" if rec.get("fallback") else "—",
                rec.get("fallback_reason", ""),
            ]
            for c, v in enumerate(cells):
                item = QTableWidgetItem(v)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if rec.get("fallback") and c == 6:
                    item.setForeground(Qt.GlobalColor.darkRed)
                self.table.setItem(r, c, item)

        if total == 0:
            self.status.setText(f"Sin registros · archivo: {paths.API_LOG_FILE}")
        else:
            self.status.setText(f"{total} registros · archivo: {paths.API_LOG_FILE.name}")
