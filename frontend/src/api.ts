import type { DashboardPayload, LiveAssetBoardItem } from "./types";

const browserHost = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
const API_BASE = `http://${browserHost}:8000/api/v1`;

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Falha ao carregar ${path}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getDashboard: () => request<DashboardPayload>("/dashboard"),
  getLiveBoard: () => request<LiveAssetBoardItem[]>("/market/live-board"),
  getExportJson: () => request<DashboardPayload>("/reports/export"),
  refreshLiveBoard: async () => {
    const response = await fetch(`${API_BASE}/market/live-board/refresh`, { method: "POST" });
    if (!response.ok) {
      throw new Error("Falha ao atualizar a varredura ao vivo");
    }
    return response.json() as Promise<LiveAssetBoardItem[]>;
  },
  exportCsv: async () => {
    const response = await fetch(`${API_BASE}/reports/export.csv`);
    if (!response.ok) {
      throw new Error("Falha ao exportar CSV");
    }
    return response.text();
  }
};
