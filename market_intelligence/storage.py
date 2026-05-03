from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from market_intelligence.models import DecisionResult, MacroEvent


class MarketIntelligenceStorage:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "decision_history.jsonl"
        self.events_cache = self.storage_dir / "macro_events_cache.json"

    def save_decision(self, decision: DecisionResult) -> None:
        latest_path = self.storage_dir / f"latest_{self._safe_name(decision.asset)}_{decision.timeframe}.json"
        latest_path.write_text(json.dumps(decision.to_dict(), indent=2, ensure_ascii=True), encoding="utf-8")
        with self.history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(decision.to_dict(), ensure_ascii=True) + "\n")

    def load_latest_decision(self, asset: str, timeframe: str) -> DecisionResult | None:
        latest_path = self.storage_dir / f"latest_{self._safe_name(asset)}_{timeframe}.json"
        if not latest_path.exists():
            return None
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
        return DecisionResult.from_dict(payload)

    def save_events(self, events: list[MacroEvent]) -> None:
        payload = [
            {
                "event_time": event.event_time.isoformat(),
                "title": event.title,
                "impact": event.impact,
                "source": event.source,
                "region": event.region,
                "related_assets": event.related_assets,
            }
            for event in events
        ]
        self.events_cache.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    def load_events(self) -> list[MacroEvent]:
        if not self.events_cache.exists():
            return []
        payload = json.loads(self.events_cache.read_text(encoding="utf-8"))
        return [
            MacroEvent(
                event_time=datetime.fromisoformat(item["event_time"]),
                title=item["title"],
                impact=item["impact"],
                source=item["source"],
                region=item["region"],
                related_assets=list(item.get("related_assets", [])),
            )
            for item in payload
        ]

    @staticmethod
    def _safe_name(value: str) -> str:
        return value.replace("/", "_").replace(" ", "_").lower()
