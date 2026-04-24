CREATE INDEX IF NOT EXISTS ix_candles_asset_timeframe_timestamp ON candles (asset, timeframe, timestamp);
CREATE INDEX IF NOT EXISTS ix_indicators_asset_timeframe_timestamp ON indicators (asset, timeframe, timestamp);
CREATE INDEX IF NOT EXISTS ix_decision_signals_asset_timeframe_created_at ON decision_signals (asset, timeframe, created_at);
CREATE INDEX IF NOT EXISTS ix_market_snapshots_symbol_timeframe_created_at ON market_snapshots (symbol, timeframe, created_at);
CREATE INDEX IF NOT EXISTS ix_market_news_scope_published_at ON market_news (asset_scope, published_at);
CREATE INDEX IF NOT EXISTS ix_economic_events_region_event_time ON economic_events (region, event_time);
