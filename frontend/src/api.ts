import type { DashboardSummary, EconomicEventItem, OpportunityCard, SignalItem } from "./types";

const API_BASE = "http://localhost:8000/api/v1";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Falha ao carregar ${path}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getSummary: () => request<DashboardSummary>("/dashboard/summary"),
  getSignals: () => request<SignalItem[]>("/signals"),
  getOpportunities: () => request<OpportunityCard[]>("/opportunities"),
  getEconomicEvents: () => request<EconomicEventItem[]>("/economic-events")
};
