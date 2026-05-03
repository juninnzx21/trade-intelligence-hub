from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout


class IntelligencePanel(QFrame):
    def __init__(self, on_analyze: Callable[[str, str], None], on_send_signal: Callable[[], None]) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._on_analyze = on_analyze
        self._on_send_signal = on_send_signal

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        title = QLabel("Inteligencia de Mercado")
        title.setObjectName("SectionLabel")
        subtitle = QLabel("Analise local ou online usando fontes publicas e oficiais antes de qualquer decisao operacional.")
        subtitle.setObjectName("MutedLabel")
        subtitle.setWordWrap(True)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.asset_input = QLineEdit()
        self.asset_input.setPlaceholderText("EUR/USD ou BTC/USDT")
        self.timeframe_input = QComboBox()
        self.timeframe_input.addItems(["M1", "M5", "M15", "H1"])
        self.analyze_button = QPushButton("Atualizar Analise")
        self.analyze_button.setObjectName("PrimaryButton")
        self.send_signal_button = QPushButton("Enviar para Sinais")
        self.send_signal_button.setObjectName("GhostButton")

        form.addWidget(QLabel("Ativo"), 0, 0)
        form.addWidget(self.asset_input, 0, 1)
        form.addWidget(QLabel("Timeframe"), 1, 0)
        form.addWidget(self.timeframe_input, 1, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(self.analyze_button)
        buttons.addWidget(self.send_signal_button)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self.mode_label = QLabel("-")
        self.action_label = QLabel("NAO_OPERAR")
        self.score_label = QLabel("0")
        self.validity_label = QLabel("-")
        self.sources_label = QLabel("-")
        self.blocks_label = QLabel("-")
        self.blocks_label.setWordWrap(True)

        grid.addWidget(QLabel("Modo"), 0, 0)
        grid.addWidget(self.mode_label, 0, 1)
        grid.addWidget(QLabel("Decisao"), 1, 0)
        grid.addWidget(self.action_label, 1, 1)
        grid.addWidget(QLabel("Score"), 2, 0)
        grid.addWidget(self.score_label, 2, 1)
        grid.addWidget(QLabel("Valido ate"), 3, 0)
        grid.addWidget(self.validity_label, 3, 1)
        grid.addWidget(QLabel("Fontes"), 4, 0)
        grid.addWidget(self.sources_label, 4, 1)
        grid.addWidget(QLabel("Bloqueios"), 5, 0)
        grid.addWidget(self.blocks_label, 5, 1)

        self.reasons_box = QTextEdit()
        self.reasons_box.setReadOnly(True)
        self.reasons_box.setMaximumHeight(220)

        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addLayout(form)
        outer.addLayout(buttons)
        outer.addLayout(grid)
        outer.addWidget(self.reasons_box)

        self.analyze_button.clicked.connect(self._handle_analyze)
        self.send_signal_button.clicked.connect(self._on_send_signal)

    def _handle_analyze(self) -> None:
        self._on_analyze(self.asset_input.text().strip(), self.timeframe_input.currentText())

    def update_analysis(self, payload: dict) -> None:
        self.mode_label.setText(str(payload.get("mode", "-")))
        self.action_label.setText(str(payload.get("action", "NAO_OPERAR")))
        self.score_label.setText(str(payload.get("confidence_score", 0)))
        self.validity_label.setText(str(payload.get("valid_until", "-")))
        self.sources_label.setText(", ".join(payload.get("data_sources", [])) or "-")
        self.blocks_label.setText("\n".join(payload.get("blocks", [])) or "-")
        reasons = payload.get("reasons", [])
        self.reasons_box.setPlainText("\n".join(reasons) if reasons else "Sem motivos adicionais.")
