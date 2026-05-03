from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


def badge_object_name(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {"OK", "DEMO", "DEMO_ARMADO", "VALIDADO"}:
        return "BadgeOk"
    if normalized in {"DRY_RUN", "ALERTA", "ATENCAO", "DESCONHECIDO"}:
        return "BadgeWarn"
    if normalized in {"PARADO", "FALHA", "BLOQUEADO", "REAL"}:
        return "BadgeDanger"
    return "BadgeInfo"


class StatusCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MutedLabel")
        self.value_label = QLabel(value)
        self.value_label.setWordWrap(True)
        self.value_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("MutedLabel")
        self.subtitle_label.setWordWrap(True)
        self.badge = QLabel(value)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setObjectName(badge_object_name(value))

        top_row = QHBoxLayout()
        top_row.addWidget(self.title_label)
        top_row.addStretch(1)
        top_row.addWidget(self.badge)

        layout.addLayout(top_row)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def update_content(self, value: str, subtitle: str = "") -> None:
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)
        self.badge.setText(value)
        self.badge.setObjectName(badge_object_name(value))
        self.style().unpolish(self.badge)
        self.style().polish(self.badge)
