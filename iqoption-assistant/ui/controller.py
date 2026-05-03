from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys

from PySide6.QtCore import QUrl
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QDesktopServices

from config import resolve_base_dir

BASE_DIR = resolve_base_dir()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(BASE_DIR.parent))

from audit_exporter import AuditExporter
from auto_trader import AutoTrader, TraderSnapshot
from browser_controller import BrowserController, BrowserSession
from config import Settings, load_settings
from integrity_guard import IntegrityGuard
from main import build_logger
from pin_guard import PinGuard
from risk_guard import ArmSessionContext, can_arm_session
from security import SecurityManager
from signal_parser import TradeSignal, parse_signal_input
from market_intelligence import MarketIntelligenceEngine, load_market_intelligence_config
from market_intelligence.api_client import MarketIntelligenceApiClient
from market_intelligence.models import DecisionResult
from market_intelligence.storage import MarketIntelligenceStorage


@dataclass
class PendingSignal:
    asset: str
    direction: str
    entry_time: str
    expiration: str
    status: str
    signal: TradeSignal


def _format_signal_timeframe(value: str) -> str:
    mapping = {"1M": "M1", "5M": "M5", "15M": "M15", "1H": "H1", "M1": "M1", "M5": "M5", "M15": "M15", "H1": "H1"}
    return mapping.get(value.strip().upper(), "M1")


class AutomationWorker(QObject):
    status_changed = Signal(dict)
    signals_changed = Signal(list)
    analysis_changed = Signal(dict)
    toast = Signal(str, str)
    action_finished = Signal(str, bool)

    def __init__(self) -> None:
        super().__init__()
        self.settings: Settings | None = None
        self.logger: logging.Logger | None = None
        self.security: SecurityManager | None = None
        self.pin_guard: PinGuard | None = None
        self.integrity_guard: IntegrityGuard | None = None
        self.audit_exporter: AuditExporter | None = None
        self.browser_controller: BrowserController | None = None
        self.browser_session: BrowserSession | None = None
        self.trader: AutoTrader | None = None
        self.market_config = None
        self.market_storage: MarketIntelligenceStorage | None = None
        self.market_engine: MarketIntelligenceEngine | None = None
        self.market_api_client: MarketIntelligenceApiClient | None = None
        self.latest_analysis: DecisionResult | None = None
        self.pending_signals: list[PendingSignal] = []
        self._poll_timer: QTimer | None = None
        self._busy = False

    @Slot()
    def initialize(self) -> None:
        self.settings = load_settings(BASE_DIR)
        self.logger = build_logger(self.settings.logs_dir, self.settings.log_level)
        self.security = SecurityManager(self.settings)
        self.pin_guard = PinGuard(self.settings, self.logger)
        self.integrity_guard = IntegrityGuard(self.settings)
        self.audit_exporter = AuditExporter(self.settings, self.logger)
        self.security.harden_local_storage()
        self.security.warn_if_unsealed(self.logger)
        self.pin_guard.ensure_pin_hash()
        self.market_config = load_market_intelligence_config(BASE_DIR)
        self.market_storage = MarketIntelligenceStorage(self.market_config.storage_dir)
        if self.market_config.market_mode == "online" and self.market_config.market_api_url:
            self.market_api_client = MarketIntelligenceApiClient(
                self.market_config.market_api_url,
                token=self.market_config.market_api_token,
                timeout_seconds=self.market_config.request_timeout_seconds,
            )
        else:
            self.market_engine = MarketIntelligenceEngine(self.market_config, self.market_storage)
        self.browser_controller = BrowserController(self.settings, self.logger)
        self.trader = AutoTrader(
            settings=self.settings,
            controller=self.browser_controller,
            logger=self.logger,
            security=self.security,
            pin_guard=self.pin_guard,
            integrity_guard=self.integrity_guard,
            status_callback=self._handle_snapshot,
            event_callback=self._handle_event,
        )

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._process_queue)
        self._poll_timer.start(1000)
        self._emit_status()
        self._emit_signal_rows()
        self._emit_analysis()

    @Slot()
    def open_iq_option(self) -> None:
        try:
            assert self.browser_controller is not None
            if self.browser_session is None:
                self.browser_session = self.browser_controller.connect()
            self.browser_controller.open_traderoom(self.browser_session.page)
            login_ready = self.browser_controller.wait_for_manual_login(self.browser_session.page, interactive=False)
            if not login_ready:
                self.toast.emit("warning", "Login manual necessario. Entre na IQ Option no Chrome e depois volte ao app.")
                self._update_runtime_status(account="DESCONHECIDO", last_event="Aguardando login manual.")
                return
            account = self.browser_controller.detect_account_mode(self.browser_session.page)
            guidance = (
                "Conta DEMO confirmada. Traderoom pronta no Chrome."
                if account == "DEMO"
                else "Conta REAL detectada. START seguira bloqueado."
                if account == "REAL"
                else "Nao foi possivel confirmar conta DEMO. Selecione manualmente Conta Demo na IQ Option e clique em Atualizar Conta."
            )
            self._update_runtime_status(account=account, last_event=guidance)
            if account == "REAL":
                self.toast.emit("error", guidance)
            self.action_finished.emit("Abrir IQ Option", True)
        except Exception as exc:
            self._handle_failure("Abrir IQ Option", exc)

    @Slot()
    def refresh_account(self) -> None:
        try:
            assert self.browser_controller is not None
            if self.browser_session is None:
                self.toast.emit("warning", "Abra a IQ Option antes de atualizar a conta.")
                return
            account = self.browser_controller.detect_account_mode(self.browser_session.page)
            message = (
                "Conta DEMO confirmada."
                if account == "DEMO"
                else "Conta REAL detectada. START continuara bloqueado."
                if account == "REAL"
                else "Nao foi possivel confirmar conta DEMO. Selecione manualmente Conta Demo na IQ Option e clique em Atualizar Conta."
            )
            self._update_runtime_status(account=account, last_event=message)
            level = "success" if account == "DEMO" else "error" if account == "REAL" else "warning"
            self.toast.emit(level, message)
            self.action_finished.emit("Atualizar Conta", account == "DEMO")
        except Exception as exc:
            self._handle_failure("Atualizar Conta", exc)

    @Slot(str)
    def start_automation(self, pin: str) -> None:
        try:
            if not pin.strip():
                self.toast.emit("error", "PIN nao informado.")
                return
            assert self.pin_guard is not None
            assert self.integrity_guard is not None
            assert self.trader is not None
            assert self.browser_controller is not None

            if self.browser_session is None:
                self.toast.emit("error", "Abra a IQ Option antes de iniciar a automacao.")
                return

            if not self.pin_guard.validate_pin(pin):
                status = self.pin_guard.status()
                reason = "PIN bloqueado nesta sessao." if status.blocked else f"PIN invalido. Tentativas restantes: {status.remaining_attempts}"
                self.toast.emit("error", reason)
                self._emit_status()
                return

            integrity = self.integrity_guard.check_integrity()
            self.trader.integrity_status = integrity.status
            if not integrity.ok:
                self.toast.emit("error", "Falha na integridade local. Regrave o manifesto antes de seguir.")
                self._emit_status()
                return

            page = self.browser_session.page
            account_mode = self.browser_controller.detect_account_mode(page)
            preview_guard = can_arm_session(
                self.settings,
                ArmSessionContext(
                    pin_validated=self.pin_guard.is_validated(),
                    pin_blocked=self.pin_guard.status().blocked,
                    integrity_ok=integrity.ok,
                    stop_flag_exists=self.settings.stop_file.exists(),
                    account_mode=account_mode,
                ),
            )
            if not preview_guard.allowed:
                self.toast.emit("error", preview_guard.reason)
                self._update_runtime_status(account=account_mode, last_event=preview_guard.reason)
                return

            decision = self.trader.arm_demo_session(account_mode)
            level = "success" if decision.allowed else "error"
            self.toast.emit(level, decision.reason)
            self.action_finished.emit("START", decision.allowed)
            self._emit_status()
        except Exception as exc:
            self._handle_failure("START", exc)

    @Slot()
    def stop_automation(self) -> None:
        try:
            assert self.trader is not None
            self.trader.request_stop("STOP acionado pela GUI")
            self.toast.emit("warning", "Automacao parada pelo usuario.")
            self.action_finished.emit("STOP", True)
            self._emit_status()
        except Exception as exc:
            self._handle_failure("STOP", exc)

    @Slot()
    def clear_stop_flag(self) -> None:
        try:
            assert self.trader is not None
            self.trader.clear_stop_flag()
            self.toast.emit("info", "STOP flag removida.")
            self._emit_status()
        except Exception as exc:
            self._handle_failure("Limpar STOP", exc)

    @Slot()
    def verify_integrity(self) -> None:
        try:
            assert self.integrity_guard is not None
            result = self.integrity_guard.check_integrity()
            if self.trader is not None:
                self.trader.integrity_status = result.status
            level = "success" if result.ok else "error"
            self.toast.emit(level, "\n".join(result.details))
            self.action_finished.emit("Verificar Integridade", result.ok)
            self._emit_status()
        except Exception as exc:
            self._handle_failure("Verificar Integridade", exc)

    @Slot()
    def write_integrity(self) -> None:
        try:
            assert self.integrity_guard is not None
            path = self.integrity_guard.write_manifest()
            if self.trader is not None:
                self.trader.integrity_status = "OK"
            self.toast.emit("success", f"Manifesto gerado em {path}")
            self._emit_status()
        except Exception as exc:
            self._handle_failure("Gerar Integridade", exc)

    @Slot()
    def export_audit(self) -> None:
        try:
            assert self.audit_exporter is not None
            path = self.audit_exporter.export()
            self.toast.emit("success", f"Auditoria exportada para {path}")
            self.action_finished.emit("Exportar Auditoria", True)
            self._emit_status()
        except Exception as exc:
            self._handle_failure("Exportar Auditoria", exc)

    @Slot(str, str)
    def analyze_market(self, asset: str, timeframe: str) -> None:
        try:
            if not asset.strip():
                self.toast.emit("warning", "Informe um ativo para analisar.")
                return
            if self.market_config is None:
                self.toast.emit("error", "Configuracao de inteligencia indisponivel.")
                return
            if self.market_config.market_mode == "online":
                if self.market_api_client is None:
                    raise RuntimeError("MARKET_MODE=online sem MARKET_API_URL configurado.")
                decision = self.market_api_client.analyze(asset.strip(), timeframe)
            else:
                if self.market_engine is None:
                    raise RuntimeError("Engine local de market intelligence nao inicializada.")
                decision = self.market_engine.analyze_market(asset.strip(), timeframe)
            self.latest_analysis = decision
            self.toast.emit("success" if decision.action != "NAO_OPERAR" else "warning", f"Analise concluida: {decision.action}")
            self._emit_analysis()
            self._update_runtime_status(next_signal=f"{decision.asset} {decision.action} {decision.timeframe}", last_event=f"Analise atualizada: {decision.action}")
        except Exception as exc:
            self._handle_failure("Atualizar Analise", exc)

    @Slot()
    def send_analysis_to_signals(self) -> None:
        try:
            if self.latest_analysis is None:
                self.toast.emit("warning", "Nenhuma analise disponivel para envio.")
                return
            if self.latest_analysis.action == "NAO_OPERAR":
                self.toast.emit("warning", "A analise atual bloqueou a operacao. Nada sera enviado para sinais.")
                return
            entry_at = datetime.now().astimezone().replace(second=0, microsecond=0) + timedelta(minutes=1)
            item = PendingSignal(
                asset=self.latest_analysis.asset,
                direction=self.latest_analysis.action,
                entry_time=entry_at.strftime("%H:%M"),
                expiration=_format_signal_timeframe(self.latest_analysis.timeframe),
                status="PENDENTE",
                signal=parse_signal_input(
                    asset=self.latest_analysis.asset,
                    direction=self.latest_analysis.action,
                    entry_time_text=entry_at.strftime("%H:%M"),
                    expiration=_format_signal_timeframe(self.latest_analysis.timeframe),
                ),
            )
            self.pending_signals.append(item)
            self.pending_signals.sort(key=lambda row: row.signal.entry_at)
            self.toast.emit("info", f"Analise enviada para sinais: {item.asset} {item.direction}.")
            self._emit_signal_rows()
            self._update_runtime_status(next_signal=f"{item.asset} {item.direction} {item.entry_time} {item.expiration}", last_event="Analise convertida em sinal pendente.")
        except Exception as exc:
            self._handle_failure("Enviar para Sinais", exc)

    @Slot(str, str, str, str)
    def add_signal(self, asset: str, direction: str, entry_time: str, expiration: str) -> None:
        try:
            signal = parse_signal_input(asset=asset, direction=direction, entry_time_text=entry_time, expiration=expiration)
            item = PendingSignal(
                asset=signal.asset,
                direction=signal.direction,
                entry_time=signal.entry_at.strftime("%H:%M"),
                expiration=signal.expiration,
                status="PENDENTE",
                signal=signal,
            )
            self.pending_signals.append(item)
            self.pending_signals.sort(key=lambda row: row.signal.entry_at)
            self.toast.emit("info", f"Sinal {signal.direction} {signal.asset} adicionado.")
            self._emit_signal_rows()
            if self.trader is not None:
                self.trader.next_signal = f"{item.asset} {item.direction} {item.entry_time} {item.expiration}"
                self.trader.last_event = "Fila de sinais atualizada."
                self._emit_status()
        except Exception as exc:
            self._handle_failure("Adicionar Sinal", exc)

    @Slot()
    def open_logs_folder(self) -> None:
        if self.settings is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.settings.logs_dir)))

    @Slot()
    def open_readme(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(BASE_DIR / "README.md")))

    @Slot()
    def shutdown(self) -> None:
        if self.browser_session is not None:
            self.browser_session.close()
            self.browser_session = None
        if self._poll_timer is not None:
            self._poll_timer.stop()

    def _process_queue(self) -> None:
        if self._busy or not self.pending_signals or self.browser_session is None or self.trader is None:
            self._emit_status()
            return

        item = self.pending_signals[0]
        if item.status not in {"PENDENTE", "ERRO"}:
            self.pending_signals.pop(0)
            self._emit_signal_rows()
            return

        self._busy = True
        item.status = "PROCESSANDO"
        self._emit_signal_rows()
        try:
            decision = self.trader.process_signal(item.signal, self.browser_session.page, allow_click_demo_only_flag=True)
            item.status = "EXECUTADO" if decision.allowed else "MANUAL"
            self.toast.emit("success" if decision.allowed else "warning", decision.reason)
        except Exception as exc:
            item.status = "ERRO"
            self._handle_failure("Processar Sinal", exc)
        finally:
            self._busy = False
            self.pending_signals.pop(0)
            self._emit_signal_rows()
            self._emit_status()

    def _emit_signal_rows(self) -> None:
        payload = [
            {
                "asset": item.asset,
                "direction": item.direction,
                "entry_time": item.entry_time,
                "expiration": item.expiration,
                "status": item.status,
            }
            for item in self.pending_signals
        ]
        self.signals_changed.emit(payload)

    def _emit_analysis(self) -> None:
        mode = self.market_config.market_mode.upper() if self.market_config is not None else "LOCAL"
        if self.latest_analysis is None:
            self.analysis_changed.emit(
                {
                    "mode": mode,
                    "action": "NAO_OPERAR",
                    "confidence_score": 0,
                    "valid_until": "-",
                    "reasons": ["Nenhuma analise executada ainda."],
                    "blocks": [],
                    "data_sources": [],
                }
            )
            return
        payload = self.latest_analysis.to_dict()
        payload["mode"] = mode
        self.analysis_changed.emit(payload)

    def _handle_snapshot(self, snapshot: TraderSnapshot) -> None:
        self.status_changed.emit(asdict(snapshot))

    def _handle_event(self, message: str) -> None:
        self.toast.emit("info", message)
        self._emit_status()

    def _update_runtime_status(
        self,
        *,
        account: str | None = None,
        current_asset: str | None = None,
        next_signal: str | None = None,
        last_event: str | None = None,
    ) -> None:
        if self.trader is None:
            return
        if account is not None:
            self.trader.account_status = account
        if current_asset is not None:
            self.trader.current_asset = current_asset
        if next_signal is not None:
            self.trader.next_signal = next_signal
        if last_event is not None:
            self.trader.last_event = last_event
        self._emit_status()

    def _emit_status(self) -> None:
        if self.trader is None or self.settings is None or self.security is None:
            return
        if self.browser_session is not None and self.browser_controller is not None:
            try:
                page = self.browser_session.page
                if self.browser_controller.browser_alive(page):
                    self.trader.account_status = self.browser_controller.detect_account_mode(page, verbose=False)
                    current_asset = self.browser_controller.detect_current_asset(page)
                    if current_asset:
                        self.trader.current_asset = current_asset
            except Exception:
                pass
        snapshot = asdict(self.trader.snapshot())
        snapshot.update(
            {
                "dry_run": self.settings.dry_run,
                "allow_auto_click": self.settings.allow_auto_click,
                "demo_only": self.settings.demo_only,
                "market_mode": self.market_config.market_mode if self.market_config is not None else "local",
                "encryption_ready": self.security.encryption_ready,
                "audit_file": str(self.settings.encrypted_audit_file),
                "stop_flag_exists": self.settings.stop_file.exists(),
                "integrity_manifest": str(self.settings.integrity_manifest),
            }
        )
        self.status_changed.emit(snapshot)

    def _handle_failure(self, action: str, exc: Exception) -> None:
        if self.logger is not None:
            self.logger.exception("Falha em %s", action)
        message = f"{action} falhou: {exc}"
        self.toast.emit("error", message)
        self.action_finished.emit(action, False)
        if self.trader is not None:
            self.trader.last_event = message
            self._emit_status()


class UiController(QObject):
    status_changed = Signal(dict)
    signals_changed = Signal(list)
    analysis_changed = Signal(dict)
    toast = Signal(str, str)
    action_finished = Signal(str, bool)

    request_open_iq_option = Signal()
    request_refresh_account = Signal()
    request_start = Signal(str)
    request_stop = Signal()
    request_clear_stop = Signal()
    request_verify_integrity = Signal()
    request_write_integrity = Signal()
    request_export_audit = Signal()
    request_add_signal = Signal(str, str, str, str)
    request_analyze_market = Signal(str, str)
    request_send_analysis_to_signals = Signal()
    request_open_logs_folder = Signal()
    request_open_readme = Signal()
    request_shutdown = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.thread = QThread()
        self.worker = AutomationWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.initialize)
        self.request_open_iq_option.connect(self.worker.open_iq_option)
        self.request_refresh_account.connect(self.worker.refresh_account)
        self.request_start.connect(self.worker.start_automation)
        self.request_stop.connect(self.worker.stop_automation)
        self.request_clear_stop.connect(self.worker.clear_stop_flag)
        self.request_verify_integrity.connect(self.worker.verify_integrity)
        self.request_write_integrity.connect(self.worker.write_integrity)
        self.request_export_audit.connect(self.worker.export_audit)
        self.request_add_signal.connect(self.worker.add_signal)
        self.request_analyze_market.connect(self.worker.analyze_market)
        self.request_send_analysis_to_signals.connect(self.worker.send_analysis_to_signals)
        self.request_open_logs_folder.connect(self.worker.open_logs_folder)
        self.request_open_readme.connect(self.worker.open_readme)
        self.request_shutdown.connect(self.worker.shutdown)

        self.worker.status_changed.connect(self.status_changed)
        self.worker.signals_changed.connect(self.signals_changed)
        self.worker.analysis_changed.connect(self.analysis_changed)
        self.worker.toast.connect(self.toast)
        self.worker.action_finished.connect(self.action_finished)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.request_shutdown.emit()
        self.thread.quit()
        self.thread.wait(3000)
