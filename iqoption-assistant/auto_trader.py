from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import time

from browser_controller import BrowserController
from config import Settings
from floating_stop import FloatingStopPanel, PanelState
from risk_guard import ExecutionContext, GuardDecision, can_auto_click, is_demo_account, pre_click_guard, signal_in_execution_window
from signal_parser import BRAZIL_TZ, TradeSignal


@dataclass
class SessionState:
    session_armed: bool = False
    trades_executed: int = 0
    operation_in_progress: bool = False
    stop_requested: bool = False
    stop_reason: str = ""


class AutoTrader:
    def __init__(self, settings: Settings, controller: BrowserController, panel: FloatingStopPanel | None, logger: logging.Logger) -> None:
        self.settings = settings
        self.controller = controller
        self.panel = panel
        self.logger = logger
        self.state = SessionState(stop_requested=settings.stop_file.exists(), stop_reason="STOP flag ja existia." if settings.stop_file.exists() else "")
        self.current_asset = "-"
        self.next_signal = "-"
        self._refresh_panel()

    def arm_demo_session(self, account_label: str) -> GuardDecision:
        if self.state.stop_requested or self.settings.stop_file.exists():
            return GuardDecision(False, "Sessao bloqueada: STOP ativo.")
        if not self.settings.session_arm_required:
            self.state.session_armed = True
            self._refresh_panel()
            return GuardDecision(True, "Sessao armada sem requisito adicional.")
        if not is_demo_account(account_label):
            return GuardDecision(False, "Conta nao confirmada como DEMO.")
        self.state.session_armed = True
        self.logger.warning("Sessao DEMO armada manualmente.")
        self._refresh_panel()
        return GuardDecision(True, "Sessao DEMO armada.")

    def request_stop(self, reason: str) -> None:
        self.state.stop_requested = True
        self.state.stop_reason = reason
        self.state.session_armed = False
        self.state.operation_in_progress = False
        self.settings.stop_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings.stop_file.write_text(reason, encoding="utf-8")
        self.logger.warning("Automacao parada | motivo=%s", reason)
        self._refresh_panel()

    def process_signal(self, signal: TradeSignal, page, allow_click_demo_only_flag: bool) -> GuardDecision:
        self.next_signal = f"{signal.asset} {signal.direction} {signal.entry_at.strftime('%H:%M')} {signal.expiration}"
        self._refresh_panel()
        self.logger.info("Sinal recebido | ativo=%s direcao=%s horario=%s expiracao=%s", signal.asset, signal.direction, signal.entry_at.isoformat(), signal.expiration)

        if self.state.stop_requested or self.settings.stop_file.exists():
            return GuardDecision(False, "STOP ativo.")
        if not self.controller.ensure_page_ready(page):
            self.request_stop("Erro ou travamento de pagina.")
            return GuardDecision(False, "Pagina nao responsiva.")

        selected = self.controller.select_asset(page, signal.asset)
        asset_matches = self.controller.asset_matches_signal(page, signal.asset)
        self.current_asset = self.controller.detect_current_asset(page) or signal.asset
        self._refresh_panel()
        if not selected or not asset_matches:
            self.request_stop("Mudanca de ativo inesperada ou ativo nao confirmado.")
            return GuardDecision(False, "Ativo nao confirmado com seguranca.")

        if not self._wait_until_signal(signal, page):
            return GuardDecision(False, self.state.stop_reason or "Sinal cancelado.")

        account_label = self.controller.detect_account_label(page)
        account_is_demo = is_demo_account(account_label)
        click_guard = can_auto_click(
            settings=self.settings,
            allow_click_demo_only_flag=allow_click_demo_only_flag,
            account_is_demo=account_is_demo,
            confirmation_text="CONFIRMO DEMO" if self.state.session_armed else None,
        )
        context = ExecutionContext(
            session_armed=self.state.session_armed,
            account_is_demo=account_is_demo,
            active_asset_matches=self.controller.asset_matches_signal(page, signal.asset),
            stop_flag_exists=self.settings.stop_file.exists() or self.state.stop_requested,
            trades_executed=self.state.trades_executed,
            operation_in_progress=self.state.operation_in_progress,
            browser_alive=self.controller.browser_alive(page),
        )

        if click_guard.allowed:
            decision = pre_click_guard(self.settings, signal, context, now=datetime.now(BRAZIL_TZ))
            if not decision.allowed:
                if "expirou" in decision.reason.lower():
                    self.request_stop("Passou do horario do sinal.")
                return decision
            self.state.operation_in_progress = True
            try:
                clicked = self.controller.click_direction_demo_only(page, signal.direction)
                if not clicked:
                    self.request_stop("Falha ao clicar no botao da direcao.")
                    return GuardDecision(False, "Nao foi possivel clicar no botao com seguranca.")
                self.state.trades_executed += 1
                self.logger.warning("Clique DEMO executado | ativo=%s direcao=%s total=%s", signal.asset, signal.direction, self.state.trades_executed)
                if self.state.trades_executed >= self.settings.max_trades_per_session:
                    self.request_stop("Limite maximo de operacoes atingido.")
                else:
                    self._refresh_panel()
                return GuardDecision(True, "Clique DEMO executado com protecoes ativas.")
            finally:
                self.state.operation_in_progress = False
        self.controller.highlight_direction(page, signal.direction)
        return click_guard

    def _wait_until_signal(self, signal: TradeSignal, page) -> bool:
        alert_sent = False
        while True:
            if self.state.stop_requested or self.settings.stop_file.exists():
                self.request_stop("STOP acionado durante espera.")
                return False
            if not self.controller.browser_alive(page):
                self.request_stop("Navegador fechado.")
                return False
            if not self.controller.asset_matches_signal(page, signal.asset):
                self.request_stop("Ativo mudou inesperadamente durante a espera.")
                return False

            now = datetime.now(BRAZIL_TZ)
            window_check = signal_in_execution_window(signal, now=now)
            seconds_left = (signal.entry_at - now).total_seconds()
            if window_check.allowed:
                return True
            if "expirou" in window_check.reason.lower():
                self.request_stop("Passou do horario do sinal.")
                return False
            if not alert_sent and seconds_left <= self.settings.alert_before_seconds:
                print(f"[ALERTA] Faltam {max(0, int(seconds_left))}s para {signal.direction} {signal.asset} {signal.expiration}.")
                self.logger.info("Alerta emitido | ativo=%s direcao=%s faltam=%s", signal.asset, signal.direction, int(seconds_left))
                alert_sent = True
            time.sleep(1)

    def _refresh_panel(self) -> None:
        if self.panel is None:
            return
        status = "PARADO" if self.state.stop_requested else ("DEMO_ARMADO" if self.state.session_armed else "DRY_RUN")
        self.panel.update(PanelState(status=status, current_asset=self.current_asset, next_signal=self.next_signal))
