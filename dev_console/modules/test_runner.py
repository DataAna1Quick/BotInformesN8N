"""Tab 5 — run the full pipeline locally with a chosen Excel + logo."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from .. import paths

# Make `core` importable.
sys.path.insert(0, str(paths.STREAMLIT_DIR))


class PipelineWorker(QObject):
    log = pyqtSignal(str)
    done = pyqtSignal(bytes, dict, str)  # pptx_bytes, meta, error

    def __init__(self, excel_bytes: bytes, logo_bytes: bytes | None,
                 client_name: str, use_llm: bool, api_key: str | None):
        super().__init__()
        self.excel_bytes = excel_bytes
        self.logo_bytes = logo_bytes
        self.client_name = client_name
        self.use_llm = use_llm
        self.api_key = api_key

    def run(self):
        try:
            from core.pipeline import run_pipeline_full
            result = run_pipeline_full(
                self.excel_bytes, self.logo_bytes, self.client_name,
                use_llm=self.use_llm, api_key=self.api_key,
                progress_cb=lambda m: self.log.emit(m),
            )
            self.done.emit(result["pptx_bytes"], result, "")
        except Exception as e:
            self.done.emit(b"", {}, f"{type(e).__name__}: {e}")


class TestRunner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "Corre el pipeline completo localmente con los mismos módulos "
            "que usa Streamlit. Útil para validar cambios en prompts, paleta o slides."
        ))

        row = QHBoxLayout()
        row.addWidget(QLabel("Excel:"))
        self.excel_path = QLineEdit()
        self.excel_path.setText(str(paths.FIXTURES_DIR / "n8n_sample.xlsx"))
        row.addWidget(self.excel_path, 1)
        b = QPushButton("…")
        b.clicked.connect(lambda: self._pick(self.excel_path, "Excel (*.xlsx)"))
        row.addWidget(b)
        v.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Logo cliente:"))
        self.logo_path = QLineEdit()
        self.logo_path.setText(str(paths.FIXTURES_DIR / "client_logo_sample.png"))
        row2.addWidget(self.logo_path, 1)
        b2 = QPushButton("…")
        b2.clicked.connect(lambda: self._pick(self.logo_path, "Imagen (*.png *.jpg)"))
        row2.addWidget(b2)
        v.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Cliente:"))
        self.client_name = QLineEdit("Cliente Demo")
        row3.addWidget(self.client_name, 1)
        v.addLayout(row3)

        row4 = QHBoxLayout()
        self.use_llm = QCheckBox("Análisis con IA (Claude Haiku)")
        row4.addWidget(self.use_llm)
        row4.addStretch(1)
        v.addLayout(row4)

        self.btn_run = QPushButton("▶ Generar PPT de prueba")
        self.btn_run.setDefault(True)
        self.btn_run.clicked.connect(self._on_run)
        v.addWidget(self.btn_run)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        v.addWidget(self.log, 1)

    def _pick(self, line: QLineEdit, filt: str):
        f, _ = QFileDialog.getOpenFileName(self, "Selecciona archivo",
                                           line.text(), filt)
        if f:
            line.setText(f)

    def _on_run(self):
        excel = Path(self.excel_path.text())
        if not excel.exists():
            QMessageBox.warning(self, "Excel no encontrado", str(excel))
            return
        logo_bytes = None
        logo = Path(self.logo_path.text())
        if logo.exists():
            logo_bytes = logo.read_bytes()

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.use_llm.isChecked() and not api_key:
            QMessageBox.warning(
                self, "Falta API key",
                "Configura ANTHROPIC_API_KEY en el entorno antes de activar IA.",
            )
            return

        self.log.clear()
        self.btn_run.setEnabled(False)

        self._thread = QThread(self)
        self._worker = PipelineWorker(
            excel.read_bytes(), logo_bytes, self.client_name.text().strip(),
            self.use_llm.isChecked(), api_key,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self._append_log)
        self._worker.done.connect(self._on_done)
        self._thread.start()

    def _append_log(self, msg: str):
        self.log.appendPlainText(msg)

    def _on_done(self, pptx_bytes: bytes, meta: dict, err: str):
        self._thread.quit()
        self._thread.wait()
        self.btn_run.setEnabled(True)

        if err:
            QMessageBox.critical(self, "Falló", err)
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if c.isalnum() else "_" for c in self.client_name.text())
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PPT generado",
            str(paths.ROOT / "output" / f"PPT_{safe}_{ts}.pptx"),
            "PowerPoint (*.pptx)",
        )
        if not out_path:
            return
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(pptx_bytes)
        self.log.appendPlainText(f"\nGuardado en: {out_path}")
        if QMessageBox.question(self, "Abrir", "¿Abrir el PPT generado?") == QMessageBox.StandardButton.Yes:
            os.startfile(out_path)  # type: ignore[attr-defined]
