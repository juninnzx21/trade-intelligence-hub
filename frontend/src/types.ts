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

export interface IntegrationStatus {
  name: string;
  category: string;
  status: string;
  auth_type: string;
  base_url: string;
  notes: string;
}

export interface ModuleStatus {
  name: string;
  mode: string;
  enabled: boolean;
  description: string;
}

export interface AssetConfigItem {
  symbol: string;
  market: string;
  provider: string;
  priority: number;
  enabled: boolean;
  timeframes: string[];
}

export interface RiskProfileItem {
  profile_name: string;
  stake_percent: number;
  daily_stop_percent: number;
  daily_target_percent: number;
  max_consecutive_losses: number;
  cooldown_minutes: number;
  observer_mode: boolean;
}

export interface BacktestMetricItem {
  strategy_name: string;
  symbol: string;
  timeframe: string;
  win_rate: number;
  payoff: number;
  drawdown: number;
  net_profit: number;
  worst_streak: number;
  best_hour: string;
  risk_label: string;
}

export interface ForwardTestMetricItem {
  window_name: string;
  signals_count: number;
  win_rate: number;
  average_score: number;
  status: string;
  notes: string;
}

export interface AuditLogItem {
  created_at: string;
  actor: string;
  action: string;
  details: string;
}

export interface LiveAssetBoardItem {
  symbol: string;
  market: string;
  timeframe: string;
  provider: string;
  score: number;
  decision: string;
  risk_level: string;
  trend: string;
  spread: number;
  volatility: number;
  reasons: string[];
  blockers: string[];
  indicator_snapshot: Record<string, string | number | boolean>;
}

export interface DashboardPayload {
  summary: DashboardSummary;
  opportunities: OpportunityCard[];
  live_board: LiveAssetBoardItem[];
  signals: SignalItem[];
  economic_events: EconomicEventItem[];
  integrations: IntegrationStatus[];
  modules: ModuleStatus[];
  monitored_assets: AssetConfigItem[];
  risk_profile: RiskProfileItem;
  backtests: BacktestMetricItem[];
  forward_tests: ForwardTestMetricItem[];
  audits: AuditLogItem[];
}
