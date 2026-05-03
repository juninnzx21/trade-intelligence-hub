from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib import request

from market_intelligence.config import MarketIntelligenceConfig
from market_intelligence.models import CollectorIssue, MacroEvent


class MacroCalendarCollector:
    MONTHS = {
        "JANUARY": 1,
        "FEBRUARY": 2,
        "MARCH": 3,
        "APRIL": 4,
        "MAY": 5,
        "JUNE": 6,
        "JULY": 7,
        "AUGUST": 8,
        "SEPTEMBER": 9,
        "OCTOBER": 10,
        "NOVEMBER": 11,
        "DECEMBER": 12,
    }

    def __init__(self, config: MarketIntelligenceConfig) -> None:
        self.config = config

    def fetch_upcoming_events(self, now: datetime) -> tuple[list[MacroEvent], list[CollectorIssue]]:
        events: list[MacroEvent] = []
        issues: list[CollectorIssue] = []
        fed_events, fed_issues = self._fetch_fed_events(now)
        ecb_events, ecb_issues = self._fetch_ecb_events(now)
        events.extend(fed_events)
        events.extend(ecb_events)
        issues.extend(fed_issues)
        issues.extend(ecb_issues)
        upcoming = [item for item in events if item.event_time >= now - timedelta(minutes=self.config.block_news_minutes_after)]
        upcoming.sort(key=lambda item: item.event_time)
        return upcoming[:10], issues

    def _fetch_fed_events(self, now: datetime) -> tuple[list[MacroEvent], list[CollectorIssue]]:
        try:
            with request.urlopen("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", timeout=self.config.request_timeout_seconds) as response:
                html = response.read().decode("utf-8", errors="ignore").upper()
        except Exception as exc:
            return [], [CollectorIssue(source="fed-calendar", message=f"Falha ao consultar calendario do Fed: {exc}", critical=False)]

        events: list[MacroEvent] = []
        year = now.year
        for month_name, day1, day2 in re.findall(r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{1,2})-(\d{1,2})", html):
            month = self.MONTHS.get(month_name)
            if not month:
                continue
            event_time = datetime(year, month, int(day1), 13, 0, tzinfo=timezone.utc)
            if event_time >= now - timedelta(days=1):
                events.append(MacroEvent(event_time=event_time, title="FOMC Meeting Window", impact="HIGH", source="federalreserve.gov", region="US", related_assets=["FOREX", "CRYPTO"]))
        return events[:8], []

    def _fetch_ecb_events(self, now: datetime) -> tuple[list[MacroEvent], list[CollectorIssue]]:
        try:
            with request.urlopen("https://www.ecb.europa.eu/ecb/access_to_documents/document/calendars/html/index.en.html", timeout=self.config.request_timeout_seconds) as response:
                html = response.read().decode("utf-8", errors="ignore").upper()
        except Exception as exc:
            return [], [CollectorIssue(source="ecb-calendar", message=f"Falha ao consultar calendario do ECB: {exc}", critical=False)]

        events: list[MacroEvent] = []
        year = now.year
        for match in re.findall(r"CALENDAR OF .*? ([A-Z]+) (\d{4})", html):
            month_name, match_year = match
            if int(match_year) != year:
                continue
            month = self.MONTHS.get(month_name)
            if not month:
                continue
            event_time = datetime(year, month, 15, 12, 0, tzinfo=timezone.utc)
            if event_time >= now - timedelta(days=1):
                events.append(MacroEvent(event_time=event_time, title="ECB Calendar Risk Window", impact="MEDIUM", source="ecb.europa.eu", region="EU", related_assets=["FOREX"]))
        return events[:6], []
