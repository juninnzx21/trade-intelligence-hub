from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from audit_exporter import AuditExporter
from config import load_settings
from integrity_guard import IntegrityGuard
from pin_guard import PinGuard
from security import RedactingFilter, SecurityManager
from signal_parser import TradeSignal, parse_signal_input


def build_logger(logs_dir: Path, level: str) -> logging.Logger:
    logger = logging.getLogger("iqoption_assistant")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(logs_dir / "trading-assistant.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.addFilter(RedactingFilter())
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assistente local seguro para preparar a IQ Option em modo observador.")
    parser.add_argument("--allow-click-demo-only", action="store_true", help="Permite clique experimental apenas em conta DEMO e com confirmacao manual.")
    parser.add_argument("--write-integrity", action="store_true", help="Gera o manifesto local de integridade.")
    parser.add_argument("--check-integrity", action="store_true", help="Valida os hashes dos arquivos monitorados.")
    parser.add_argument("--export-audit", action="store_true", help="Exporta a trilha de auditoria cifrada para formato legivel.")
    parser.add_argument("--signal-text")
    parser.add_argument("--ativo")
    parser.add_argument("--direcao")
    parser.add_argument("--horario")
    parser.add_argument("--expiracao")
    return parser.parse_args()


def ask_if_missing(value: str | None, label: str) -> str:
    if value:
        return value
    return input(f"{label}: ").strip()


def collect_signal(args: argparse.Namespace) -> TradeSignal:
    if args.signal_text:
        return parse_signal_input(raw_text=args.signal_text)
    return parse_signal_input(
        asset=ask_if_missing(args.ativo, "ativo"),
        direction=ask_if_missing(args.direcao, "direcao"),
        entry_time_text=ask_if_missing(args.horario, "horario"),
        expiration=ask_if_missing(args.expiracao, "expiracao"),
    )


def confirmation_prompt(signal: TradeSignal) -> bool:
    print(
        f"Confirmar entrada? ativo={signal.asset} direcao={signal.direction} "
        f"horario={signal.entry_at.strftime('%H:%M')} expiracao={signal.expiration}"
    )
    return input("Digite SIM para continuar: ").strip().upper() == "SIM"


def _handle_start_event(
    trader: AutoTrader,
    controller: BrowserController,
    page,
    logger: logging.Logger,
    pin_guard: PinGuard,
    integrity_guard: IntegrityGuard,
    reason: str,
    pin: str | None,
) -> None:
    try:
        if not pin:
            message = "START cancelado: PIN nao informado."
            logger.warning(message)
            trader.panel.show_message(message) if trader.panel is not None else None
            return
        if not pin_guard.validate_pin(pin):
            status = pin_guard.status()
            message = "START bloqueado: PIN bloqueado." if status.blocked else f"START bloqueado: PIN invalido. Tentativas restantes: {status.remaining_attempts}"
            logger.warning(message)
            trader.panel.show_message(message) if trader.panel is not None else None
            trader._refresh_panel()
            return
        integrity = integrity_guard.check_integrity()
        trader.integrity_status = integrity.status
        if not integrity.ok:
            message = "START bloqueado: falha na integridade local."
            logger.error("%s | detalhes=%s", message, "; ".join(integrity.details))
            trader.panel.show_message(message) if trader.panel is not None else None
            trader.security.audit_event("integrity_check_failed", {"details": integrity.details})
            trader._refresh_panel()
            return
        account_label = controller.detect_account_label(page)
        decision = trader.arm_demo_session(account_label)
        logger.info("Armar sessao | allowed=%s | reason=%s | source=%s", decision.allowed, decision.reason, reason)
        if trader.panel is not None:
            trader.panel.show_message(decision.reason)
    except Exception as exc:
        logger.error("Falha ao iniciar automacao: %s", exc)
        trader.request_stop("Erro ao iniciar automacao")


def main() -> int:
    args = parse_args()
    settings = load_settings()
    logger = build_logger(settings.logs_dir, settings.log_level)
    security = SecurityManager(settings)
    pin_guard = PinGuard(settings, logger)
    integrity_guard = IntegrityGuard(settings)
    audit_exporter = AuditExporter(settings, logger)
    security.harden_local_storage()
    security.warn_if_unsealed(logger)
    pin_guard.ensure_pin_hash()

    if args.write_integrity:
        manifest_path = integrity_guard.write_manifest()
        print(f"Manifesto gerado em: {manifest_path}")
        return 0

    if args.check_integrity:
        result = integrity_guard.check_integrity()
        print(f"Integridade: {result.status}")
        for detail in result.details:
            print(f"- {detail}")
        return 0 if result.ok else 1

    if args.export_audit:
        try:
            export_path = audit_exporter.export()
        except RuntimeError as exc:
            print(f"Falha segura ao exportar auditoria: {exc}")
            return 1
        print(f"Auditoria exportada para: {export_path}")
        return 0

    panel: FloatingStopPanel | None = None
    trader_holder: dict[str, AutoTrader] = {}

    from auto_trader import AutoTrader
    from browser_controller import BrowserController
    from floating_stop import FloatingStopPanel

    controller = BrowserController(settings, logger)
    session = controller.connect()

    try:
        trader = AutoTrader(
            settings=settings,
            controller=controller,
            panel=panel,
            logger=logger,
            security=security,
            pin_guard=pin_guard,
            integrity_guard=integrity_guard,
        )
        trader.integrity_status = integrity_guard.check_integrity().status
        trader_holder["instance"] = trader
        panel = FloatingStopPanel(
            on_start=lambda reason, pin: logger.info("Evento START recebido: %s | pin_informado=%s", reason, bool(pin)),
            on_stop=lambda reason: trader_holder["instance"].request_stop(reason),
            logger=logger,
        )
        trader.panel = panel
        panel.start()
        trader._refresh_panel()

        logger.info("Iniciando iqoption-assistant | dry_run=%s demo_only=%s allow_auto_click=%s session_arm_required=%s", settings.dry_run, settings.demo_only, settings.allow_auto_click, settings.session_arm_required)
        security.audit_event("assistant_started", {
            "dry_run": settings.dry_run,
            "demo_only": settings.demo_only,
            "allow_auto_click": settings.allow_auto_click,
            "session_arm_required": settings.session_arm_required,
            "encryption_ready": security.encryption_ready,
        })
        controller.open_traderoom(session.page)
        controller.wait_for_manual_login(session.page)

        panel.on_start = lambda reason, pin: _handle_start_event(trader, controller, session.page, logger, pin_guard, integrity_guard, reason, pin)

        while True:
            if trader.state.stop_requested:
                print(f"Automacao parada pelo usuario: {trader.state.stop_reason}")
                return 0

            signal = collect_signal(args)
            if not trader.state.session_armed and not confirmation_prompt(signal):
                logger.warning("Operacao cancelada pelo usuario antes do agendamento.")
                print("Operacao cancelada.")
                if args.signal_text:
                    return 0
                continue

            decision = trader.process_signal(signal, session.page, allow_click_demo_only_flag=args.allow_click_demo_only)
            print(decision.reason)
            if decision.allowed:
                print(f"Operacao demo processada: {signal.direction} {signal.asset} {signal.expiration}")
            else:
                print(f"Entrada autorizada manualmente: {signal.direction} {signal.asset} {signal.expiration}")
                controller.highlight_direction(session.page, signal.direction)
                if signal.direction == "COMPRA":
                    print("Clique manualmente em COMPRA.")
                else:
                    print("Clique manualmente em VENDA.")

            if args.signal_text:
                return 0
            print("Digite o proximo sinal ou Ctrl+C para sair.")
        return 0
    finally:
        logger.info("Sessao encerrada.")
        security.audit_event("assistant_stopped", {"panel_present": panel is not None})
        if panel is not None:
            panel.stop()
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
