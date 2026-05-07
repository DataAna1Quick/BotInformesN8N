"""Tab 1 — edit the indicator-analyst system prompt and run a smoke call."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from .. import paths


class PromptTestWorker(QThread):
    """Run a tiny LLM call in background to validate the edited prompt."""
    done = pyqtSignal(str, bool)  # (message, ok)

    def __init__(self, api_key: str, prompt: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.prompt = prompt

    def run(self):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key, timeout=20)
            r = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=20,
                system=self.prompt,
                messages=[{"role": "user", "content": "Saluda en una palabra."}],
            )
            text = r.content[0].text if r.content else "(sin respuesta)"
            self.done.emit(f"OK · respuesta: {text}", True)
        except Exception as e:
            self.done.emit(f"ERROR · {type(e).__name__}: {e}", False)


class PromptEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._reload()

    def _build(self):
        v = QVBoxLayout(self)

        hint = QLabel(
            "Edita el system prompt del sub-agente Indicator Analyst. "
            "Los cambios se guardan en core/prompts/indicator_analyst.md y son "
            "leídos automáticamente por la app Streamlit en la próxima generación."
        )
        hint.setWordWrap(True)
        v.addWidget(hint)

        self.editor = QPlainTextEdit()
        font = QFont("Cascadia Mono")
        if not font.exactMatch():
            font = QFont("Consolas")
        font.setPointSize(10)
        self.editor.setFont(font)
        v.addWidget(self.editor, 1)

        # API key + test buttons row
        row = QHBoxLayout()
        row.addWidget(QLabel("API key:"))
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("sk-ant-… (o usa $ANTHROPIC_API_KEY)")
        self.api_key.setText(os.environ.get("ANTHROPIC_API_KEY", ""))
        row.addWidget(self.api_key, 1)
        self.btn_test = QPushButton("Probar prompt")
        self.btn_test.clicked.connect(self._on_test)
        row.addWidget(self.btn_test)
        v.addLayout(row)

        # Save / reload row
        row2 = QHBoxLayout()
        self.status = QLabel("")
        row2.addWidget(self.status, 1)
        self.btn_reload = QPushButton("Recargar desde disco")
        self.btn_reload.clicked.connect(self._reload)
        row2.addWidget(self.btn_reload)
        self.btn_save = QPushButton("Guardar")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save)
        row2.addWidget(self.btn_save)
        v.addLayout(row2)

    def _reload(self):
        if paths.PROMPT_FILE.exists():
            self.editor.setPlainText(paths.PROMPT_FILE.read_text(encoding="utf-8"))
            self.status.setText(f"Cargado · {paths.PROMPT_FILE.name}")
        else:
            self.editor.setPlainText("# Prompt no encontrado.\n")
            self.status.setText("Archivo no existe; se creará al guardar.")

    def _save(self):
        try:
            paths.PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
            paths.PROMPT_FILE.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.status.setText(f"Guardado · {paths.PROMPT_FILE.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    def _on_test(self):
        key = self.api_key.text().strip() or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            QMessageBox.warning(self, "Falta API key",
                                "Ingresa una API key o configura ANTHROPIC_API_KEY.")
            return
        self.btn_test.setEnabled(False)
        self.status.setText("Probando contra Claude…")
        self._worker = PromptTestWorker(key, self.editor.toPlainText())
        self._worker.done.connect(self._on_test_done)
        self._worker.start()

    def _on_test_done(self, msg: str, ok: bool):
        self.btn_test.setEnabled(True)
        self.status.setText(msg)
