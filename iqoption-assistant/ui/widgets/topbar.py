from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton

from ui.widgets.status_card import badge_object_name


class Topbar(QFrame):
    def __init__(self, on_stop: Callable[[], None], on_toggle_topmost: Callable[[bool], None]) -> None:
        super().__init__()
        self.setObjectName("Topbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        self.title = QLabel("IQ Option Assistant")
        self.title.setObjectName("TitleLabel")

        self.status_badge = QLabel("PARADO")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setObjectName("BadgeStopped")
        self.env_badge = QLabel("DESCONHECIDO")
        self.env_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.env_badge.setObjectName("BadgeDanger")

        self.topmost_toggle = QCheckBox("Sempre no topo")
        self.topmost_toggle.toggled.connect(on_toggle_topmost)

        self.stop_button = QPushButton("STOP")
        self.stop_button.setObjectName("DangerButton")
        self.stop_button.clicked.connect(on_stop)

        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(self.status_badge)
        layout.addWidget(self.env_badge)
        layout.addWidget(self.topmost_toggle)
        layout.addWidget(self.stop_button)

    def update_status(self, status: str, environment: str) -> None:
        self.status_badge.setText(status)
        self.status_badge.setObjectName(badge_object_name(status))
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

        self.env_badge.setText(environment)
        self.env_badge.setObjectName(badge_object_name(environment))
        self.env_badge.style().unpolish(self.env_badge)
        self.env_badge.style().polish(self.env_badge)

