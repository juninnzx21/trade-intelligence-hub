from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class MarketIntelligenceConfig:
    root_dir: Path
    storage_dir: Path
    market_mode: str
    market_api_url: str
    market_api_token: str
    oanda_api_token: str
    oanda_account_id: str
    oanda_base_url: str
    fred_api_key: str
    bls_api_key: str
    min_confidence_score: int
    block_news_minutes_before: int
    block_news_minutes_after: int
    request_timeout_seconds: int
    fred_dxy_series_id: str
    fred_yield_series_id: str
    bls_cpi_series_id: str
    bls_payroll_series_id: str


def load_market_intelligence_config(root_dir: Path) -> MarketIntelligenceConfig:
    storage_dir = root_dir / "storage" / "market_intelligence"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return MarketIntelligenceConfig(
        root_dir=root_dir,
        storage_dir=storage_dir,
        market_mode=os.getenv("MARKET_MODE", "local").strip().lower() or "local",
        market_api_url=os.getenv("MARKET_API_URL", "").strip(),
        market_api_token=os.getenv("MARKET_API_TOKEN", "").strip(),
        oanda_api_token=os.getenv("OANDA_API_TOKEN", os.getenv("OANDA_API_KEY", "")).strip(),
        oanda_account_id=os.getenv("OANDA_ACCOUNT_ID", "").strip(),
        oanda_base_url=os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com").strip(),
        fred_api_key=os.getenv("FRED_API_KEY", "").strip(),
        bls_api_key=os.getenv("BLS_API_KEY", "").strip(),
        min_confidence_score=int(os.getenv("MIN_CONFIDENCE_SCORE", "70")),
        block_news_minutes_before=int(os.getenv("BLOCK_NEWS_MINUTES_BEFORE", "30")),
        block_news_minutes_after=int(os.getenv("BLOCK_NEWS_MINUTES_AFTER", "15")),
        request_timeout_seconds=int(os.getenv("MARKET_REQUEST_TIMEOUT_SECONDS", "10")),
        fred_dxy_series_id=os.getenv("FRED_DXY_SERIES_ID", "DTWEXBGS").strip(),
        fred_yield_series_id=os.getenv("FRED_YIELD_SERIES_ID", "DGS10").strip(),
        bls_cpi_series_id=os.getenv("BLS_CPI_SERIES_ID", "CUUR0000SA0").strip(),
        bls_payroll_series_id=os.getenv("BLS_PAYROLL_SERIES_ID", "CES0000000001").strip(),
    )
