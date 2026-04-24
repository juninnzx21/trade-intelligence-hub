export interface DashboardSummary {
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
  no_trade_signals: number;
  win_rate: number;
  best_symbol: string;
  best_timeframe: string;
  active_alerts: number;
  premium_opportunities: number;
}

export interface SignalItem {
  id: number;
  timestamp: string;
  symbol: string;
  market: string;
  timeframe: string;
  decision: string;
  score: number;
  risk_level: string;
  trend: string;
  reasoning: string;
}

export interface OpportunityCard {
  symbol: string;
  market: string;
  timeframe: string;
  score: number;
  decision: string;
  risk_level: string;
  trend: string;
  reasons: string[];
}

export interface EconomicEventItem {
  event_time: string;
  region: string;
  title: string;
  impact: string;
  source: string;
  summary: string;
}
