from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout


class ControlPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(16)

        title = QLabel("Painel de Controle")
        title.setObjectName("SectionLabel")
        subtitle = QLabel("Arme a sessao demo com PIN, valide integridade e controle a automacao em tempo real.")
        subtitle.setObjectName("MutedLabel")
        subtitle.setWordWrap(True)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.start_button = QPushButton("START")
        self.start_button.setObjectName("PrimaryButton")
        self.stop_button = QPushButton("STOP")
        self.stop_button.setObjectName("DangerButton")
        self.integrity_button = QPushButton("Verificar Integridade")
        self.audit_button = QPushButton("Exportar Auditoria")
        self.open_button = QPushButton("Abrir IQ Option")
        self.clear_stop_button = QPushButton("Limpar STOP flag")
        self.clear_stop_button.setObjectName("GhostButton")

        grid.addWidget(self.start_button, 0, 0)
        grid.addWidget(self.stop_button, 0, 1)
        grid.addWidget(self.integrity_button, 1, 0)
        grid.addWidget(self.audit_button, 1, 1)
        grid.addWidget(self.open_button, 2, 0)
        grid.addWidget(self.clear_stop_button, 2, 1)

        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addLayout(grid)

