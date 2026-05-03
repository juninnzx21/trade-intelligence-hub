from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout


class SafetyPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        title = QLabel("Seguranca")
        title.setObjectName("SectionLabel")
        subtitle = QLabel("Todos os guardas ativos para impedir operacao em conta real e execucoes fora do contexto DEMO.")
        subtitle.setObjectName("MutedLabel")
        subtitle.setWordWrap(True)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(10)

        self.values: dict[str, QLabel] = {}
        labels = [
            ("DRY_RUN", "DRY_RUN"),
            ("ALLOW_AUTO_CLICK", "ALLOW_AUTO_CLICK"),
            ("DEMO_ONLY", "DEMO_ONLY"),
            ("PIN", "PIN"),
            ("Integridade", "Integridade"),
            ("Criptografia", "Criptografia"),
            ("Auditoria", "Auditoria"),
        ]
        for row, (title_text, key) in enumerate(labels):
            title_label = QLabel(title_text)
            title_label.setObjectName("MutedLabel")
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            self.values[key] = value_label
            self.grid.addWidget(title_label, row, 0)
            self.grid.addWidget(value_label, row, 1)

        self.test_button = QPushButton("Testar Guardas")
        self.test_button.setObjectName("GhostButton")
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setMaximumHeight(140)

        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addLayout(self.grid)
        outer.addWidget(self.test_button)
        outer.addWidget(self.result_box)

    def update_values(self, values: dict[str, str]) -> None:
        for key, label in self.values.items():
            label.setText(values.get(key, "-"))

    def set_result(self, text: str) -> None:
        self.result_box.setPlainText(text)

