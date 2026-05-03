from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from config import Settings
from signal_parser import BRAZIL_TZ, TradeSignal


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class ExecutionContext:
    session_armed: bool
    account_is_demo: bool
    active_asset_matches: bool
    stop_flag_exists: bool
    trades_executed: int
    operation_in_progress: bool
    browser_alive: bool


@dataclass(frozen=True)
class ArmSessionContext:
    pin_validated: bool
    pin_blocked: bool
    integrity_ok: bool
    stop_flag_exists: bool
    account_is_demo: bool


def signal_in_execution_window(signal: TradeSignal, now: datetime | None = None, tolerance_seconds: int = 5) -> GuardDecision:
    current = now.astimezone(BRAZIL_TZ) if now else datetime.now(BRAZIL_TZ)
    delta = (current - signal.entry_at).total_seconds()
    if delta < 0:
        return GuardDecision(False, "Bloqueado: horario do sinal ainda nao chegou.")
    if delta > tolerance_seconds:
        return GuardDecision(False, "Bloqueado: horario do sinal expirou.")
    return GuardDecision(True, "Horario dentro da janela permitida.")


def is_demo_account(label_text: str | None) -> bool:
    if not label_text:
        return False
    normalized = label_text.upper()
    return any(token in normalized for token in ("DEMO", "PRACTICE", "TREINO", "TREINAMENTO"))


def can_auto_click(
    settings: Settings,
    allow_click_demo_only_flag: bool,
    account_is_demo: bool,
    confirmation_text: str | None,
) -> GuardDecision:
    if settings.dry_run:
        return GuardDecision(False, "Bloqueado: DRY_RUN=true.")
    if not settings.demo_only:
        return GuardDecision(False, "Bloqueado: DEMO_ONLY=false.")
    if not settings.allow_auto_click:
        return GuardDecision(False, "Bloqueado: ALLOW_AUTO_CLICK=false.")
    if not allow_click_demo_only_flag:
        return GuardDecision(False, "Bloqueado: flag --allow-click-demo-only ausente.")
    if not account_is_demo:
        return GuardDecision(False, "Bloqueado: conta atual nao parece ser DEMO.")
    if (confirmation_text or "").strip().upper() != "CONFIRMO DEMO":
        return GuardDecision(False, "Bloqueado: confirmacao explicita de DEMO nao recebida.")
    return GuardDecision(True, "Auto-click demo autorizado.")


def ensure_real_account_protection(account_is_demo: bool, demo_only: bool) -> GuardDecision:
    if demo_only and not account_is_demo:
        return GuardDecision(False, "Protecao ativa: conta real ou nao identificada.")
    return GuardDecision(True, "Conta compativel com modo observador.")


def can_arm_session(settings: Settings, context: ArmSessionContext) -> GuardDecision:
    if context.pin_blocked:
        return GuardDecision(False, "START bloqueado: PIN bloqueado nesta sessao.")
    if not context.pin_validated:
        return GuardDecision(False, "START bloqueado: PIN nao validado.")
    if not context.integrity_ok:
        return GuardDecision(False, "START bloqueado: integridade local falhou.")
    if context.stop_flag_exists:
        return GuardDecision(False, "START bloqueado: STOP flag ativa.")
    if settings.dry_run:
        return GuardDecision(False, "START bloqueado: DRY_RUN=true.")
    if not settings.allow_auto_click:
        return GuardDecision(False, "START bloqueado: ALLOW_AUTO_CLICK=false.")
    if not settings.demo_only:
        return GuardDecision(False, "START bloqueado: DEMO_ONLY=false.")
    if not context.account_is_demo:
        return GuardDecision(False, "START bloqueado: conta nao confirmada como DEMO.")
    return GuardDecision(True, "Sessao pronta para DEMO_ARMADO.")


def pre_click_guard(settings: Settings, signal: TradeSignal, context: ExecutionContext, now: datetime | None = None) -> GuardDecision:
    if settings.dry_run:
        return GuardDecision(False, "Bloqueado: DRY_RUN=true.")
    if not settings.allow_auto_click:
        return GuardDecision(False, "Bloqueado: ALLOW_AUTO_CLICK=false.")
    if settings.demo_only and not context.account_is_demo:
        return GuardDecision(False, "Bloqueado: conta nao confirmada como DEMO.")
    if settings.session_arm_required and not context.session_armed:
        return GuardDecision(False, "Bloqueado: sessao nao armada.")
    if context.stop_flag_exists:
        return GuardDecision(False, "Bloqueado: STOP flag ativa.")
    if context.operation_in_progress:
        return GuardDecision(False, "Bloqueado: operacao ja em andamento.")
    if not context.browser_alive:
        return GuardDecision(False, "Bloqueado: navegador indisponivel.")
    if not context.active_asset_matches:
        return GuardDecision(False, "Bloqueado: ativo atual difere do sinal.")
    if context.trades_executed >= settings.max_trades_per_session:
        return GuardDecision(False, "Bloqueado: limite de operacoes da sessao atingido.")
    if signal.direction not in {"COMPRA", "VENDA"}:
        return GuardDecision(False, "Bloqueado: direcao invalida.")
    return signal_in_execution_window(signal, now=now)
