from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from signal_parser import BRAZIL_TZ, build_entry_datetime, parse_signal_text


def test_parse_signal_text_success() -> None:
    now = datetime(2026, 5, 2, 14, 0, tzinfo=BRAZIL_TZ)
    signal = parse_signal_text(
        "ativo=EUR/USD\ndirecao=COMPRA\nhorario=14:35\nexpiracao=M1",
        now=now,
    )
    assert signal.asset == "EUR/USD"
    assert signal.direction == "COMPRA"
    assert signal.expiration == "M1"
    assert signal.entry_at.hour == 14
    assert signal.entry_at.minute == 35


def test_build_entry_datetime_rolls_to_next_day() -> None:
    now = datetime(2026, 5, 2, 14, 40, tzinfo=BRAZIL_TZ)
    target = build_entry_datetime("14:35", now=now)
    assert target.date().day == 3
    assert target.hour == 14
    assert target.minute == 35


def test_parse_signal_invalid_direction() -> None:
    now = datetime(2026, 5, 2, 14, 0, tzinfo=BRAZIL_TZ)
    with pytest.raises(ValueError):
        parse_signal_text("ativo=EUR/USD\ndirecao=ALTA\nhorario=14:35\nexpiracao=M1", now=now)


def test_parse_signal_pipe_format() -> None:
    now = datetime(2026, 5, 2, 14, 0, tzinfo=BRAZIL_TZ)
    signal = parse_signal_text("ativo=EUR/USD | direcao=VENDA | horario=14:35 | expiracao=M1", now=now)
    assert signal.asset == "EUR/USD"
    assert signal.direction == "VENDA"
