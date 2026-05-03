from __future__ import annotations

APP_STYLE = """
QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow {
    background-color: #0F172A;
}
QFrame#Sidebar {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 20px;
}
QFrame#Topbar {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 18px;
}
QFrame#Card {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 18px;
}
QFrame#SecondaryCard {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 16px;
}
QPushButton {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 10px 16px;
    color: #F8FAFC;
    font-weight: 600;
}
QPushButton:hover {
    border-color: #3B82F6;
}
QPushButton:pressed {
    background-color: #334155;
}
QPushButton#PrimaryButton {
    background-color: #22C55E;
    border-color: #22C55E;
    color: #02140A;
}
QPushButton#PrimaryButton:hover {
    background-color: #16A34A;
}
QPushButton#DangerButton {
    background-color: #EF4444;
    border-color: #EF4444;
    color: #FFF7F7;
}
QPushButton#DangerButton:hover {
    background-color: #DC2626;
}
QPushButton#GhostButton {
    background-color: transparent;
    border-color: #475569;
}
QPushButton#SidebarButton {
    text-align: left;
    padding: 12px 14px;
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 14px;
    color: #CBD5E1;
}
QPushButton#SidebarButton:hover {
    background-color: #1E293B;
    border-color: #334155;
}
QPushButton#SidebarButton[active="true"] {
    background-color: #1E293B;
    border-color: #3B82F6;
    color: #F8FAFC;
}
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QTimeEdit {
    background-color: #0B1220;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 8px 10px;
    color: #F8FAFC;
    selection-background-color: #3B82F6;
}
QTableWidget {
    background-color: #0B1220;
    alternate-background-color: #111827;
    border: 1px solid #334155;
    border-radius: 12px;
    gridline-color: #334155;
}
QHeaderView::section {
    background-color: #1E293B;
    color: #CBD5E1;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #334155;
}
QScrollArea, QScrollBar:vertical {
    background-color: transparent;
}
QScrollBar:vertical {
    width: 10px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background-color: #334155;
    border-radius: 5px;
}
QLabel#TitleLabel {
    font-size: 20px;
    font-weight: 700;
}
QLabel#SectionLabel {
    font-size: 15px;
    font-weight: 700;
}
QLabel#MutedLabel {
    color: #94A3B8;
}
QLabel#BadgeOk, QLabel#BadgeDemoArmed {
    background-color: rgba(34, 197, 94, 0.18);
    color: #86EFAC;
    border: 1px solid rgba(34, 197, 94, 0.4);
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 700;
}
QLabel#BadgeWarn, QLabel#BadgeDryRun {
    background-color: rgba(245, 158, 11, 0.18);
    color: #FCD34D;
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 700;
}
QLabel#BadgeDanger, QLabel#BadgeStopped {
    background-color: rgba(239, 68, 68, 0.18);
    color: #FCA5A5;
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 700;
}
QLabel#BadgeInfo {
    background-color: rgba(59, 130, 246, 0.18);
    color: #93C5FD;
    border: 1px solid rgba(59, 130, 246, 0.4);
    border-radius: 10px;
    padding: 4px 10px;
    font-weight: 700;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox::indicator:unchecked {
    border: 1px solid #475569;
    border-radius: 5px;
    background: #0B1220;
}
QCheckBox::indicator:checked {
    border: 1px solid #3B82F6;
    border-radius: 5px;
    background: #3B82F6;
}
"""


COLORS = {
    "background": "#0F172A",
    "card": "#111827",
    "card_secondary": "#1E293B",
    "border": "#334155",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "success": "#22C55E",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "info": "#3B82F6",
}

