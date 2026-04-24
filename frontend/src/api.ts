import type { DashboardPayload, LiveAssetBoardItem } from "./types";

const API_BASE = "http://localhost:8000/api/v1";

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
  refreshLiveBoard: async () => {
    const response = await fetch(`${API_BASE}/market/live-board/refresh`, { method: "POST" });
    if (!response.ok) {
      throw new Error("Falha ao atualizar a varredura ao vivo");
    }
    return response.json() as Promise<LiveAssetBoardItem[]>;
  }
};
