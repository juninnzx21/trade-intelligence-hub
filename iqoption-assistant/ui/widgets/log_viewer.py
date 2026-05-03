from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout


class LogViewer(QFrame):
    def __init__(self, log_path: Path, on_open_folder: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.log_path = log_path
        self._last_content = ""
        self._on_open_folder = on_open_folder

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Logs em Tempo Real")
        title.setObjectName("SectionLabel")
        self.filter_box = QComboBox()
        self.filter_box.addItems(["Todos", "Start/Stop", "Sinais", "Erros", "Seguranca"])
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setObjectName("GhostButton")
        self.open_folder_button = QPushButton("Abrir Pasta")
        self.open_folder_button.setObjectName("GhostButton")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.filter_box)
        header.addWidget(self.refresh_button)
        header.addWidget(self.open_folder_button)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlaceholderText("Os eventos do assistente aparecerao aqui.")

        outer.addLayout(header)
        outer.addWidget(self.text)

        self.refresh_button.clicked.connect(self.refresh_now)
        self.open_folder_button.clicked.connect(self._open_folder)
        self.filter_box.currentTextChanged.connect(lambda _value: self.refresh_now())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_now)
        self.timer.start(1500)

    def refresh_now(self) -> None:
        if not self.log_path.exists():
            self.text.setPlainText("Arquivo de log ainda nao gerado.")
            return
        content = self.log_path.read_text(encoding="utf-8", errors="ignore")
        lines = self._filter_lines(content.splitlines())[-300:]
        rendered = "\n".join(lines)
        if rendered == self._last_content:
            return
        self._last_content = rendered
        self.text.setPlainText(rendered)
        cursor = self.text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text.setTextCursor(cursor)

    def _filter_lines(self, lines: list[str]) -> list[str]:
        choice = self.filter_box.currentText()
        if choice == "Todos":
            return lines
        filters = {
            "Start/Stop": ("START", "STOP", "iniciada", "parada"),
            "Sinais": ("Sinal recebido", "Ativo", "Clique DEMO", "manual"),
            "Erros": ("ERROR", "Falha", "bloqueado"),
            "Seguranca": ("integridade", "PIN", "DEMO", "DRY_RUN"),
        }
        tokens = filters.get(choice, ())
        return [line for line in lines if any(token.lower() in line.lower() for token in tokens)]

    def _open_folder(self) -> None:
        if self._on_open_folder is not None:
            self._on_open_folder()
