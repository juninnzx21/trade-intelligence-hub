from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class Sidebar(QFrame):
    def __init__(self, on_change: Callable[[str], None]) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self._buttons: dict[str, QPushButton] = {}
        self._on_change = on_change

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(10)

        title = QLabel("IQ Option Assistant")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Controle central local")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        for key, label in (
            ("dashboard", "Dashboard"),
            ("signals", "Sinais"),
            ("intelligence", "Inteligencia"),
            ("security", "Seguranca"),
            ("logs", "Logs"),
            ("settings", "Configuracoes"),
        ):
            button = QPushButton(label)
            button.setObjectName("SidebarButton")
            button.setProperty("active", key == "dashboard")
            button.clicked.connect(lambda _checked=False, section=key: self.set_active(section))
            layout.addWidget(button)
            self._buttons[key] = button

        layout.addStretch(1)

    def set_active(self, section: str) -> None:
        for key, button in self._buttons.items():
            button.setProperty("active", key == section)
            button.style().unpolish(button)
            button.style().polish(button)
        self._on_change(section)
