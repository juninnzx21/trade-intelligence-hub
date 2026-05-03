from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QMenu,
    QLineEdit,
)

from ui.controller import UiController
from ui.widgets.control_panel import ControlPanel
from ui.widgets.log_viewer import LogViewer
from ui.widgets.metric_card import MetricCard
from ui.widgets.safety_panel import SafetyPanel
from ui.widgets.sidebar import Sidebar
from ui.widgets.signal_panel import SignalPanel
from ui.widgets.status_card import StatusCard
from ui.widgets.topbar import Topbar


class MainWindow(QMainWindow):
    def __init__(self, controller: UiController, base_dir: Path) -> None:
        super().__init__()
        self.controller = controller
        self.base_dir = base_dir
        self.current_status: dict[str, object] = {}

        self.setWindowTitle("IQ Option Assistant")
        self.resize(1100, 720)
        self.setMinimumSize(980, 640)
        self.statusBar().showMessage("Interface pronta. Abra a IQ Option para iniciar.")

        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(18)

        self.sidebar = Sidebar(self._switch_section)
        main_layout.addWidget(self.sidebar, 0)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(18)
        main_layout.addLayout(right_layout, 1)

        self.topbar = Topbar(on_stop=self._request_stop, on_toggle_topmost=self._toggle_topmost)
        right_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)

        self._build_pages()
        self._build_shortcuts()
        self._build_tray()

        self.controller.status_changed.connect(self._apply_status)
        self.controller.signals_changed.connect(self.signal_panel.update_signals)
        self.controller.toast.connect(self._show_toast)

    def _build_pages(self) -> None:
        self.dashboard_page = self._build_dashboard_page()
        self.signals_page = self._build_signals_page()
        self.security_page = self._build_security_page()
        self.logs_page = self._build_logs_page()
        self.settings_page = self._build_settings_page()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.signals_page)
        self.stack.addWidget(self.security_page)
        self.stack.addWidget(self.logs_page)
        self.stack.addWidget(self.settings_page)

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setSpacing(18)

        self.status_cards = {
            "status": StatusCard("Status da Automacao", "PARADO", "O app sempre inicia desarmado."),
            "account": StatusCard("Conta Detectada", "DESCONHECIDO", "Conta real continua bloqueada."),
            "integrity": StatusCard("Integridade", "NAO GERADA", "Gere ou valide o manifesto antes do START."),
            "pin": StatusCard("PIN", "NAO VALIDADO", "O PIN e exigido toda vez que a sessao e armada."),
        }
        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(14)
        cards_grid.setVerticalSpacing(14)
        card_values = list(self.status_cards.values())
        for idx, card in enumerate(card_values):
            cards_grid.addWidget(card, idx // 2, idx % 2)

        self.metric_cards = {
            "asset": MetricCard("Ativo Atual", "-", "Monitorado diretamente na traderoom."),
            "next_signal": MetricCard("Proximo Sinal", "-", "Fila local de sinais pendentes."),
            "trades": MetricCard("Operacoes da Sessao", "0", "Contador protegido por limite maximo."),
            "event": MetricCard("Ultimo Evento", "Inicializado", "Historico resumido em tempo real."),
        }
        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(14)
        metrics_grid.setVerticalSpacing(14)
        metric_values = list(self.metric_cards.values())
        for idx, card in enumerate(metric_values):
            metrics_grid.addWidget(card, idx // 2, idx % 2)

        self.control_panel = ControlPanel()
        self.control_panel.start_button.clicked.connect(self._request_start)
        self.control_panel.stop_button.clicked.connect(self._request_stop)
        self.control_panel.integrity_button.clicked.connect(lambda: self.controller.request_verify_integrity.emit())
        self.control_panel.audit_button.clicked.connect(lambda: self.controller.request_export_audit.emit())
        self.control_panel.open_button.clicked.connect(lambda: self.controller.request_open_iq_option.emit())
        self.control_panel.refresh_account_button.clicked.connect(lambda: self.controller.request_refresh_account.emit())
        self.control_panel.clear_stop_button.clicked.connect(lambda: self.controller.request_clear_stop.emit())

        outer.addLayout(cards_grid)
        outer.addLayout(metrics_grid)
        outer.addWidget(self.control_panel)
        outer.addStretch(1)
        return page

    def _build_signals_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        self.signal_panel = SignalPanel(
            on_add_signal=lambda asset, direction, entry, expiration: self.controller.request_add_signal.emit(asset, direction, entry, expiration)
        )
        layout.addWidget(self.signal_panel)
        return page

    def _build_security_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)
        self.safety_panel = SafetyPanel()
        self.safety_panel.test_button.clicked.connect(lambda: self.controller.request_verify_integrity.emit())
        layout.addWidget(self.safety_panel)
        return page

    def _build_logs_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)
        self.log_viewer = LogViewer(self.base_dir / "storage" / "logs" / "trading-assistant.log", on_open_folder=lambda: self.controller.request_open_logs_folder.emit())
        layout.addWidget(self.log_viewer)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        title = QLabel("Configuracoes")
        title.setObjectName("SectionLabel")
        subtitle = QLabel("Segredos aparecem mascarados. Use esta area apenas para inspeção segura e acesso rapido aos arquivos.")
        subtitle.setObjectName("MutedLabel")
        subtitle.setWordWrap(True)

        self.settings_table = QTableWidget(0, 2)
        self.settings_table.setHorizontalHeaderLabels(["Chave", "Valor"])
        self.settings_table.horizontalHeader().setStretchLastSection(True)
        self.settings_table.verticalHeader().setVisible(False)
        self.settings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.settings_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        button_row = QHBoxLayout()
        self.readme_button = QPushButton("Abrir README")
        self.readme_button.setObjectName("GhostButton")
        self.generate_manifest_button = QPushButton("Gerar Manifesto")
        self.generate_manifest_button.setObjectName("GhostButton")
        self.readme_button.clicked.connect(lambda: self.controller.request_open_readme.emit())
        self.generate_manifest_button.clicked.connect(lambda: self.controller.request_write_integrity.emit())
        button_row.addWidget(self.readme_button)
        button_row.addWidget(self.generate_manifest_button)
        button_row.addStretch(1)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.settings_table)
        card_layout.addLayout(button_row)

        layout.addWidget(card)
        return page

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, activated=self._request_start)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self._request_stop)

    def _build_tray(self) -> None:
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        tray_menu.addAction("Abrir", self.showNormal)
        tray_menu.addAction("START", self._request_start)
        tray_menu.addAction("STOP", self._request_stop)
        tray_menu.addSeparator()
        tray_menu.addAction("Sair", self.close)
        self.tray.setContextMenu(tray_menu)
        self.tray.setToolTip("IQ Option Assistant")
        self.tray.show()

    def _switch_section(self, section: str) -> None:
        index_map = {
            "dashboard": 0,
            "signals": 1,
            "security": 2,
            "logs": 3,
            "settings": 4,
        }
        self.stack.setCurrentIndex(index_map[section])

    def _toggle_topmost(self, enabled: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.show()

    def _request_start(self) -> None:
        pin, ok = QInputDialog.getText(self, "Validar PIN", "Digite o PIN local:", QLineEdit.EchoMode.Password)
        if not ok:
            return
        self.controller.request_start.emit(pin)

    def _request_stop(self) -> None:
        self.controller.request_stop.emit()

    def _show_toast(self, level: str, message: str) -> None:
        self.statusBar().showMessage(message, 8000)
        if level in {"info", "success"}:
            return
        icon_map = {
            "success": QMessageBox.Icon.Information,
            "info": QMessageBox.Icon.Information,
            "warning": QMessageBox.Icon.Warning,
            "error": QMessageBox.Icon.Critical,
        }
        box = QMessageBox(self)
        box.setWindowTitle("IQ Option Assistant")
        box.setIcon(icon_map.get(level, QMessageBox.Icon.Information))
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    def _apply_status(self, payload: dict) -> None:
        self.current_status = payload
        status = str(payload.get("status", "PARADO"))
        account = str(payload.get("account_status", "DESCONHECIDO"))
        self.topbar.update_status(status, account)

        self.status_cards["status"].update_content(status, "Controle central local do modo de execucao.")
        account_help = (
            "Conta DEMO confirmada. Auto-click continua sujeito aos demais guardas."
            if account == "DEMO"
            else "Conta REAL detectada. START segue bloqueado."
            if account == "REAL"
            else "Nao foi possivel confirmar conta DEMO. Selecione manualmente Conta Demo na IQ Option e clique em Atualizar Conta."
        )
        self.status_cards["account"].update_content(account, account_help)
        self.status_cards["integrity"].update_content(str(payload.get("integrity_status", "NAO GERADA")), str(payload.get("integrity_manifest", "")))
        self.status_cards["pin"].update_content(str(payload.get("pin_status", "NAO VALIDADO")), "PIN nunca e salvo em texto puro.")

        self.metric_cards["asset"].update_content(str(payload.get("current_asset", "-")), "Ativo lido diretamente da pagina controlada.")
        self.metric_cards["next_signal"].update_content(str(payload.get("next_signal", "-")), "A fila local e processada em background.")
        self.metric_cards["trades"].update_content(str(payload.get("trades_executed", 0)), "Limite da sessao protegido pelo RiskGuard.")
        self.metric_cards["event"].update_content(str(payload.get("last_event", "-")), "Mensagens resumidas vindas da thread de automacao.")

        self.safety_panel.update_values(
            {
                "DRY_RUN": str(payload.get("dry_run")),
                "ALLOW_AUTO_CLICK": str(payload.get("allow_auto_click")),
                "DEMO_ONLY": str(payload.get("demo_only")),
                "PIN": str(payload.get("pin_status")),
                "Integridade": str(payload.get("integrity_status")),
                "Criptografia": "ATIVA" if payload.get("encryption_ready") else "INDISPONIVEL",
                "Auditoria": str(payload.get("audit_file", "-")),
            }
        )
        guidance = (
            "Conta DEMO confirmada."
            if account == "DEMO"
            else "Conta REAL detectada. START bloqueado."
            if account == "REAL"
            else "Nao foi possivel confirmar conta DEMO. Selecione manualmente Conta Demo na IQ Option e clique em Atualizar Conta."
        )
        self.safety_panel.set_result(
            f"Conta detectada: {account}\nSTOP flag ativa: {payload.get('stop_flag_exists')}\n{guidance}"
        )
        self._update_settings_table(payload)

    def _update_settings_table(self, payload: dict) -> None:
        rows = [
            ("ASSISTANT_MASTER_KEY", "********"),
            ("ASSISTANT_PIN", "********"),
            ("DRY_RUN", str(payload.get("dry_run"))),
            ("ALLOW_AUTO_CLICK", str(payload.get("allow_auto_click"))),
            ("DEMO_ONLY", str(payload.get("demo_only"))),
            ("Audit file", str(payload.get("audit_file", "-"))),
        ]
        self.settings_table.setRowCount(len(rows))
        for row_index, (key, value) in enumerate(rows):
            self.settings_table.setItem(row_index, 0, QTableWidgetItem(key))
            self.settings_table.setItem(row_index, 1, QTableWidgetItem(value))

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.controller.stop()
        if self.tray is not None:
            self.tray.hide()
        super().closeEvent(event)
