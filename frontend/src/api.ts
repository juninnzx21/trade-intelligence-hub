import type { DashboardPayload, LiveAssetBoardItem } from "./types";

const isBrowser = typeof window !== "undefined";
const browserProtocol = isBrowser ? window.location.protocol : "http:";
const browserHost = isBrowser ? window.location.host : "127.0.0.1:8000";
const wsProtocol = browserProtocol === "https:" ? "wss:" : "ws:";
const defaultApiBase = isBrowser
  ? `${browserProtocol}//${browserHost}/api/v1`
  : "http://127.0.0.1:8000/api/v1";
const defaultWsBase = isBrowser
  ? `${wsProtocol}//${browserHost}/api/v1`
  : "ws://127.0.0.1:8000/api/v1";

const API_BASE = import.meta.env.VITE_API_BASE || defaultApiBase;
const WS_BASE = import.meta.env.VITE_WS_BASE || defaultWsBase;

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
  liveBoardSocketUrl: () => `${WS_BASE}/market/live-board/ws`,
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
