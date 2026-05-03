from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from auto_trader import AutoTrader
from browser_controller import BrowserController
from config import load_settings
from floating_stop import FloatingStopPanel
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
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assistente local seguro para preparar a IQ Option em modo observador.")
    parser.add_argument("--allow-click-demo-only", action="store_true", help="Permite clique experimental apenas em conta DEMO e com confirmacao manual.")
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


def _handle_start_event(trader: AutoTrader, controller: BrowserController, page, logger: logging.Logger, reason: str) -> None:
    try:
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
    panel: FloatingStopPanel | None = None
    trader_holder: dict[str, AutoTrader] = {}

    controller = BrowserController(settings, logger)
    session = controller.connect()

    try:
        trader = AutoTrader(settings=settings, controller=controller, panel=panel, logger=logger)
        trader_holder["instance"] = trader
        panel = FloatingStopPanel(
            on_start=lambda reason: logger.info("Evento START recebido: %s", reason),
            on_stop=lambda reason: trader_holder["instance"].request_stop(reason),
            logger=logger,
        )
        trader.panel = panel
        panel.start()
        trader._refresh_panel()

        logger.info("Iniciando iqoption-assistant | dry_run=%s demo_only=%s allow_auto_click=%s session_arm_required=%s", settings.dry_run, settings.demo_only, settings.allow_auto_click, settings.session_arm_required)
        controller.open_traderoom(session.page)
        controller.wait_for_manual_login(session.page)

        panel.on_start = lambda reason: _handle_start_event(trader, controller, session.page, logger, reason)

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
        if panel is not None:
            panel.stop()
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
