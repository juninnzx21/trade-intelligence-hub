from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QTimeEdit, QVBoxLayout


class SignalPanel(QFrame):
    def __init__(self, on_add_signal: Callable[[str, str, str, str], None]) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._on_add_signal = on_add_signal

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        title = QLabel("Painel de Sinais")
        title.setObjectName("SectionLabel")
        subtitle = QLabel("Cadastre sinais pendentes com ativo, direcao, horario e expiracao.")
        subtitle.setObjectName("MutedLabel")
        subtitle.setWordWrap(True)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.asset_input = QLineEdit()
        self.asset_input.setPlaceholderText("EUR/USD")
        self.direction_input = QComboBox()
        self.direction_input.addItems(["COMPRA", "VENDA"])
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setTime(QTime.currentTime())
        self.expiration_input = QComboBox()
        self.expiration_input.addItems(["M1", "M5", "M15", "H1"])
        self.add_button = QPushButton("Adicionar Sinal")
        self.add_button.setObjectName("PrimaryButton")

        form.addWidget(QLabel("Ativo"), 0, 0)
        form.addWidget(self.asset_input, 0, 1)
        form.addWidget(QLabel("Direcao"), 1, 0)
        form.addWidget(self.direction_input, 1, 1)
        form.addWidget(QLabel("Horario"), 2, 0)
        form.addWidget(self.time_input, 2, 1)
        form.addWidget(QLabel("Expiracao"), 3, 0)
        form.addWidget(self.expiration_input, 3, 1)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        buttons_row.addWidget(self.add_button)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Ativo", "Direcao", "Horario", "Exp.", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addLayout(form)
        outer.addLayout(buttons_row)
        outer.addWidget(self.table)

        self.add_button.clicked.connect(self._handle_add)

    def _handle_add(self) -> None:
        self._on_add_signal(
            self.asset_input.text().strip(),
            self.direction_input.currentText(),
            self.time_input.time().toString("HH:mm"),
            self.expiration_input.currentText(),
        )

    def update_signals(self, rows: list[dict[str, str]]) -> None:
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, key in enumerate(("asset", "direction", "entry_time", "expiration", "status")):
                item = QTableWidgetItem(row.get(key, ""))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_index, col_index, item)

