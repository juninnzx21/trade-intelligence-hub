<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { api } from "./api";
import type { DashboardPayload, LiveAssetBoardItem, SignalItem } from "./types";

const loading = ref(true);
const error = ref("");
const refreshingLive = ref(false);
const exportMessage = ref("");
const dashboard = ref<DashboardPayload | null>(null);
const selectedMarket = ref("TODOS");
const autoRefreshLabel = ref("Auto-refresh ativo a cada 30s");
const currentTime = ref(new Date());

let liveRefreshTimer: ReturnType<typeof setInterval> | null = null;
let clockTimer: ReturnType<typeof setInterval> | null = null;
let liveSocket: WebSocket | null = null;

const summary = computed(() => dashboard.value?.summary ?? null);
const signals = computed(() => dashboard.value?.signals ?? []);
const events = computed(() => dashboard.value?.economic_events ?? []);
const liveBoard = computed(() => dashboard.value?.live_board ?? []);
const integrations = computed(() => dashboard.value?.integrations ?? []);
const monitoredAssets = computed(() => dashboard.value?.monitored_assets ?? []);
const modules = computed(() => dashboard.value?.modules ?? []);
const riskProfile = computed(() => dashboard.value?.risk_profile ?? null);
const backtests = computed(() => dashboard.value?.backtests ?? []);
const forwardTests = computed(() => dashboard.value?.forward_tests ?? []);
const audits = computed(() => dashboard.value?.audits ?? []);
const users = computed(() => dashboard.value?.users ?? []);
const alertChannels = computed(() => dashboard.value?.alert_channels ?? []);
const securityControls = computed(() => dashboard.value?.security_controls ?? []);
const scrapingSources = computed(() => dashboard.value?.scraping_sources ?? []);

const actionableLiveBoard = computed(() =>
  liveBoard.value.filter((item) => item.decision === "COMPRA" || item.decision === "VENDA")
);

const filteredSignals = computed(() => {
  const visible = signals.value.filter((signal) => signal.decision === "COMPRA" || signal.decision === "VENDA");
  return selectedMarket.value === "TODOS"
    ? visible
    : visible.filter((signal) => signal.market === selectedMarket.value);
});

const headline = computed(() => actionableLiveBoard.value[0] ?? liveBoard.value[0] ?? null);
const actionableSignal = computed(() => actionableLiveBoard.value[0] ?? null);

async function loadDashboard() {
  loading.value = true;
  error.value = "";
  try {
    dashboard.value = await api.getDashboard();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Falha ao carregar dashboard";
  } finally {
    loading.value = false;
  }
}

async function refreshLiveBoard() {
  if (refreshingLive.value) return;
  refreshingLive.value = true;
  error.value = "";
  try {
    const board = await api.refreshLiveBoard();
    applyLiveBoard(board);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Falha ao atualizar a varredura";
  } finally {
    refreshingLive.value = false;
  }
}

function applyLiveBoard(board: LiveAssetBoardItem[]) {
  if (dashboard.value) {
    dashboard.value = { ...dashboard.value, live_board: board };
  }
}

function startLivePolling() {
  if (liveRefreshTimer) clearInterval(liveRefreshTimer);
  liveRefreshTimer = setInterval(() => {
    void refreshLiveBoard();
  }, 30000);
}

function connectLiveSocket() {
  if (typeof window === "undefined") return;
  if (liveSocket) liveSocket.close();
  liveSocket = new WebSocket(api.liveBoardSocketUrl());
  liveSocket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data) as LiveAssetBoardItem[] | { heartbeat?: boolean };
      if (Array.isArray(payload)) {
        applyLiveBoard(payload);
        autoRefreshLabel.value = "WebSocket live conectado";
      }
    } catch {
      autoRefreshLabel.value = "WebSocket instavel, fallback ativo";
    }
  };
  liveSocket.onerror = () => {
    autoRefreshLabel.value = "WebSocket instavel, fallback ativo";
  };
  liveSocket.onclose = () => {
    autoRefreshLabel.value = "Auto-refresh ativo a cada 30s";
  };
}

function startClock() {
  if (clockTimer) clearInterval(clockTimer);
  clockTimer = setInterval(() => {
    currentTime.value = new Date();
  }, 1000);
}

async function exportCsv() {
  try {
    const csv = await api.exportCsv();
    exportMessage.value = `CSV pronto com ${csv.split("\n").length - 1} linhas.`;
  } catch (err) {
    exportMessage.value = err instanceof Error ? err.message : "Falha ao exportar";
  }
}

onMounted(async () => {
  await loadDashboard();
  connectLiveSocket();
  startLivePolling();
  startClock();
});

onUnmounted(() => {
  if (liveRefreshTimer) clearInterval(liveRefreshTimer);
  if (clockTimer) clearInterval(clockTimer);
  if (liveSocket) liveSocket.close();
  liveRefreshTimer = null;
  clockTimer = null;
  liveSocket = null;
});

function decisionClass(decision: string) {
  return {
    COMPRA: "decision buy",
    VENDA: "decision sell",
    NAO_OPERAR: "decision neutral"
  }[decision] ?? "decision neutral";
}

function impactClass(impact: string) {
  return {
    ALTO: "decision sell",
    MEDIO: "decision neutral",
    BAIXO: "decision buy"
  }[impact] ?? "decision neutral";
}

function integrationClass(status: string) {
  return {
    ativo: "decision buy",
    active: "decision buy",
    observador: "decision neutral",
    observer: "decision neutral",
    planned: "decision neutral",
    pilot: "decision neutral",
    validando: "decision neutral",
    em_coleta: "decision neutral",
    designed: "decision neutral",
    "aguardando-chave": "decision neutral",
    "ready-for-env": "decision neutral",
    disabled: "decision sell"
  }[status] ?? "decision neutral";
}

function moduleClass(enabled: boolean, mode: string) {
  if (!enabled || mode === "disabled") return "decision sell";
  if (mode === "observer") return "decision neutral";
  return "decision buy";
}

function severityClass(value: string) {
  return {
    high: "decision sell",
    medium: "decision neutral",
    low: "decision buy"
  }[value] ?? "decision neutral";
}

function scoreRailStyle(score: number) {
  return { width: `${Math.max(8, Math.min(score, 100))}%` };
}

function parseDate(value: string | null | undefined) {
  return value ? new Date(value) : null;
}

function compactDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo"
  });
}

function timeOnly(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "America/Sao_Paulo"
  });
}

function nowLabel() {
  return currentTime.value.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "America/Sao_Paulo"
  });
}

function assetLabel(symbol: string | null | undefined) {
  return symbol ? `Moeda/par ${symbol}` : "Moeda/par indisponivel";
}

function reasonsText(item: LiveAssetBoardItem | SignalItem) {
  if ("reasons" in item) {
    return item.reasons.join(" • ");
  }
  return item.reasoning;
}

function rowClass(score: number) {
  if (score >= 76) return "row-strong";
  if (score <= 50) return "row-risk";
  return "";
}

function tinySeries(values: number[]) {
  if (!values.length) return "";
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 100;
      const y = 100 - ((value - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(" ");
}

const floatingGuide = computed(() => {
  const signal = actionableSignal.value;
  if (!signal) {
    return {
      title: "Nao operar agora",
      subtitle: "Nenhuma compra ou venda valida no momento.",
      action: "Aguarde a proxima janela valida.",
      tone: "neutral",
      details: ["Sistema em observacao.", `Horario atual: ${nowLabel()}`]
    };
  }

  const now = currentTime.value;
  const entry = parseDate(signal.entry_time);
  const exit = parseDate(signal.exit_time);
  const validUntil = parseDate(signal.signal_valid_until);
  const side = signal.decision === "COMPRA" ? "compra" : "venda";

  if (entry && now < entry) {
    return {
      title: `Prepare operacao de ${side}`,
      subtitle: `${assetLabel(signal.symbol)} • ${signal.timeframe}`,
      action: `Entre somente as ${timeOnly(signal.entry_time)}.`,
      tone: signal.decision === "COMPRA" ? "buy" : "sell",
      details: [
        `Horario atual: ${nowLabel()}`,
        `Moeda/par: ${signal.symbol}`,
        `Saida prevista: ${timeOnly(signal.exit_time)}`
      ]
    };
  }

  if (entry && validUntil && now >= entry && now <= validUntil) {
    return {
      title: `Entre agora com ${side}`,
      subtitle: `${assetLabel(signal.symbol)} • ${signal.timeframe}`,
      action: `Janela aberta ate ${timeOnly(signal.signal_valid_until)}.`,
      tone: signal.decision === "COMPRA" ? "buy" : "sell",
      details: [
        `Horario atual: ${nowLabel()}`,
        `Moeda/par: ${signal.symbol}`,
        `Saida prevista: ${timeOnly(signal.exit_time)}`
      ]
    };
  }

  if (validUntil && now > validUntil && exit && now < exit) {
    return {
      title: "Nao entrar atrasado",
      subtitle: `${assetLabel(signal.symbol)} • ${signal.timeframe}`,
      action: "Janela de entrada expirou. Aguarde novo sinal.",
      tone: "neutral",
      details: [
        `Horario atual: ${nowLabel()}`,
        `Moeda/par: ${signal.symbol}`,
        `Validade encerrou em: ${timeOnly(signal.signal_valid_until)}`
      ]
    };
  }

  if (exit && now >= exit) {
    return {
      title: "Ciclo encerrado",
      subtitle: `${assetLabel(signal.symbol)} • ${signal.timeframe}`,
      action: "Esse sinal ja passou. Aguarde a proxima oportunidade.",
      tone: "neutral",
      details: [
        `Horario atual: ${nowLabel()}`,
        `Moeda/par: ${signal.symbol}`,
        `Encerramento previsto: ${timeOnly(signal.exit_time)}`
      ]
    };
  }

  return {
    title: "Nao operar agora",
    subtitle: `${assetLabel(signal.symbol)} • ${signal.timeframe}`,
    action: "Contexto sem janela segura neste instante.",
    tone: "neutral",
    details: [`Horario atual: ${nowLabel()}`, `Moeda/par: ${signal.symbol}`]
  };
});

const scoreSeries = computed(() => tinySeries(actionableLiveBoard.value.map((item) => item.score)));
const backtestSeries = computed(() => tinySeries(backtests.value.map((item) => item.net_profit)));
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <p class="eyebrow">Market Decision AI</p>
        <h1>Observer Deck</h1>
        <span class="muted">Analise em modo simulador. Sem execucao automatica de ordens.</span>
      </div>

      <nav>
        <a href="#command">Command</a>
        <a href="#live-board">Live Board</a>
        <a href="#signals">Signals</a>
        <a href="#macro">Macro</a>
        <a href="#admin">Admin</a>
        <a href="#security">Security</a>
      </nav>

      <div class="sidebar-card">
        <p class="muted">Diretriz</p>
        <strong>Nao operar e uma decisao valida</strong>
        <span>O sistema privilegia bloqueio e qualidade de setup, nao volume de entrada.</span>
      </div>
    </aside>

    <main class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">Decision Engine</p>
          <h2>Analise tecnica, fundamentalista e historica em uma unica camada</h2>
        </div>
        <div class="actions">
          <button class="ghost-button" @click="loadDashboard">Recarregar</button>
          <button class="primary-button" :disabled="refreshingLive" @click="refreshLiveBoard">
            {{ refreshingLive ? "Varrendo..." : "Atualizar sinais ao vivo" }}
          </button>
        </div>
      </header>

      <section v-if="loading" class="state-card">Carregando painel...</section>
      <section v-else-if="error" class="state-card error">{{ error }}</section>

      <template v-else-if="dashboard && summary && riskProfile">
        <section id="command" class="hero-grid">
          <article class="hero-card">
            <div class="hero-copy">
              <p class="eyebrow">Sinal lider</p>
              <h3>{{ headline?.decision ?? "NAO_OPERAR" }}</h3>
              <p class="hero-subtitle">
                {{ assetLabel(headline?.symbol) }} • score {{ headline?.score ?? 0 }} • risco {{ headline?.risk_level ?? "Alto" }}
              </p>
              <div class="chip-row">
                <span class="ghost-chip">Entrada (Brasilia): {{ compactDate(headline?.entry_time) }}</span>
                <span class="ghost-chip">Saida (Brasilia): {{ compactDate(headline?.exit_time) }}</span>
                <span class="ghost-chip">Valido ate (Brasilia): {{ compactDate(headline?.signal_valid_until) }}</span>
                <span class="ghost-chip">{{ autoRefreshLabel }}</span>
              </div>
            </div>
            <div class="score-ring">
              <span>{{ Math.round(headline?.score ?? 0) }}</span>
            </div>
          </article>

          <article class="metric-card">
            <span>Sinais exibidos</span>
            <strong>{{ actionableLiveBoard.length }}</strong>
            <small class="muted">Somente compra e venda visiveis na operacao.</small>
          </article>
          <article class="metric-card">
            <span>Win rate fechado</span>
            <strong>{{ summary.win_rate }}%</strong>
            <small class="muted">Sem inventar taxa de acerto.</small>
          </article>
          <article class="metric-card">
            <span>Alertas macro</span>
            <strong>{{ summary.active_alerts }}</strong>
            <small class="muted">Eventos economicos publicos ativos.</small>
          </article>
          <article class="metric-card">
            <span>Premium raro</span>
            <strong>{{ summary.premium_opportunities }}</strong>
            <small class="muted">Pontuacoes acima de 86 sao raras por desenho.</small>
          </article>
        </section>

        <section class="command-strip">
          <div class="strip-panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Score curve</p>
                <h3>Distribuicao de oportunidade</h3>
              </div>
            </div>
            <div class="chart-shell">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                <polyline :points="scoreSeries" fill="none" stroke="currentColor" stroke-width="3" />
              </svg>
            </div>
          </div>

          <div class="strip-panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Risk posture</p>
                <h3>Regras ativas</h3>
              </div>
            </div>
            <div class="policy-grid">
              <div>
                <span class="muted">Stake</span>
                <strong>{{ riskProfile.stake_percent }}%</strong>
              </div>
              <div>
                <span class="muted">Stop diario</span>
                <strong>{{ riskProfile.daily_stop_percent }}%</strong>
              </div>
              <div>
                <span class="muted">Meta diaria</span>
                <strong>{{ riskProfile.daily_target_percent }}%</strong>
              </div>
              <div>
                <span class="muted">Cooldown</span>
                <strong>{{ riskProfile.cooldown_minutes }} min</strong>
              </div>
            </div>
          </div>
        </section>

        <section id="live-board" class="panel-grid">
          <article class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Live Board</p>
                <h3>Somente operacoes validas no radar</h3>
              </div>
              <div class="badge">Observer only</div>
            </div>

            <div v-if="actionableLiveBoard.length" class="live-grid">
              <article v-for="item in actionableLiveBoard" :key="`${item.symbol}-${item.timeframe}`" class="opportunity-card">
                <div class="row">
                  <div>
                    <strong>{{ assetLabel(item.symbol) }}</strong>
                    <p>{{ item.market }} • {{ item.timeframe }} • {{ item.provider }}</p>
                  </div>
                  <span :class="decisionClass(item.decision)">{{ item.decision }}</span>
                </div>

                <div class="score-bar">
                  <div class="fill" :style="scoreRailStyle(item.score)"></div>
                </div>

                <div class="stats-grid">
                  <span>Score {{ item.score }}</span>
                  <span>Risco {{ item.risk_level }}</span>
                  <span>Entrada {{ compactDate(item.entry_time) }}</span>
                  <span>Saida {{ compactDate(item.exit_time) }}</span>
                  <span>Duracao {{ item.duration ?? "-" }}</span>
                  <span>Valido ate {{ compactDate(item.signal_valid_until) }}</span>
                </div>

                <div class="indicator-grid">
                  <span>RSI {{ item.indicator_snapshot.rsi }}</span>
                  <span>MACD {{ item.indicator_snapshot.macd }}</span>
                  <span>ATR {{ item.indicator_snapshot.atr }}</span>
                  <span>VWAP {{ item.indicator_snapshot.vwap }}</span>
                </div>

                <ul>
                  <li v-for="reason in item.reasons.slice(0, 4)" :key="reason">{{ reason }}</li>
                </ul>
              </article>
            </div>
            <div v-else class="empty-state">
              Nenhuma compra ou venda valida agora. O sistema esta corretamente evitando operacao ruim.
            </div>
            <p class="panel-note">Horarios exibidos em America/Sao_Paulo. A varredura ao vivo atualiza automaticamente a cada 30 segundos.</p>
          </article>

          <article id="macro" class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Macro</p>
                <h3>Calendario economico</h3>
              </div>
            </div>
            <div class="event-list">
              <div v-for="event in events" :key="`${event.title}-${event.event_time}`" class="event-item">
                <div class="row meta">
                  <strong>{{ event.title }}</strong>
                  <span :class="impactClass(event.impact)">{{ event.impact }}</span>
                </div>
                <p>{{ event.region }} • {{ compactDate(event.event_time) }}</p>
                <small>{{ event.summary }}</small>
              </div>
            </div>
          </article>
        </section>

        <section id="signals" class="panel-grid">
          <article class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Signal Journal</p>
                <h3>Historico visivel apenas de compra e venda</h3>
              </div>
              <select v-model="selectedMarket" class="market-filter">
                <option value="TODOS">Todos</option>
                <option value="FOREX">Forex</option>
                <option value="CRYPTO">Cripto</option>
              </select>
            </div>

            <div v-if="filteredSignals.length" class="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>Gerado em</th>
                    <th>Moeda/Par</th>
                    <th>TF</th>
                    <th>Decisao</th>
                    <th>Entrada</th>
                    <th>Saida</th>
                    <th>Validade</th>
                    <th>Score</th>
                    <th>Resumo</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="signal in filteredSignals" :key="signal.id" :class="rowClass(signal.score)">
                    <td>{{ compactDate(signal.timestamp) }}</td>
                    <td>{{ assetLabel(signal.symbol) }}</td>
                    <td>{{ signal.timeframe }}</td>
                    <td><span :class="decisionClass(signal.decision)">{{ signal.decision }}</span></td>
                    <td>{{ compactDate(signal.entry_time) }}</td>
                    <td>{{ compactDate(signal.exit_time) }}</td>
                    <td>{{ compactDate(signal.signal_valid_until) }}</td>
                    <td>{{ signal.score }}</td>
                    <td>{{ reasonsText(signal) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-state">
              Ainda nao ha compras ou vendas para exibir neste filtro.
            </div>
          </article>

          <article class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Backtest</p>
                <h3>Strategy lab</h3>
              </div>
            </div>
            <div class="chart-shell compact">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                <polyline :points="backtestSeries" fill="none" stroke="currentColor" stroke-width="3" />
              </svg>
            </div>
            <div class="event-list">
              <div v-for="item in backtests" :key="`${item.strategy_name}-${item.symbol}`" class="event-item">
                <strong>{{ item.strategy_name }}</strong>
                <p>{{ assetLabel(item.symbol) }} • {{ item.timeframe }}</p>
                <small>Win rate {{ item.win_rate }}% • payoff {{ item.payoff }} • drawdown {{ item.drawdown }}%</small>
              </div>
            </div>
          </article>
        </section>

        <section id="admin" class="panel-grid">
          <article class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Admin</p>
                <h3>Integracoes, ativos e modulos</h3>
              </div>
            </div>
            <div class="admin-grid">
              <div class="admin-section">
                <h4>Integracoes</h4>
                <div class="stack">
                  <div v-for="item in integrations" :key="item.name" class="admin-card">
                    <div class="row">
                      <strong>{{ item.name }}</strong>
                      <span :class="integrationClass(item.status)">{{ item.status }}</span>
                    </div>
                    <p>{{ item.category }} • {{ item.auth_type }}</p>
                    <small>{{ item.notes }}</small>
                  </div>
                </div>
              </div>

              <div class="admin-section">
                <h4>Ativos monitorados</h4>
                <div class="stack">
                  <div v-for="item in monitoredAssets" :key="item.symbol" class="admin-card">
                    <div class="row">
                      <strong>{{ assetLabel(item.symbol) }}</strong>
                      <span :class="item.enabled ? 'decision buy' : 'decision sell'">{{ item.enabled ? "ativo" : "off" }}</span>
                    </div>
                    <p>{{ item.market }} • {{ item.provider }}</p>
                    <small>{{ item.timeframes.join(", ") }}</small>
                  </div>
                </div>
              </div>

              <div class="admin-section">
                <h4>Modulos</h4>
                <div class="stack">
                  <div v-for="item in modules" :key="item.name" class="admin-card">
                    <div class="row">
                      <strong>{{ item.name }}</strong>
                      <span :class="moduleClass(item.enabled, item.mode)">{{ item.mode }}</span>
                    </div>
                    <small>{{ item.description }}</small>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <article class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Forward test</p>
                <h3>Observer mode</h3>
              </div>
            </div>
            <div class="event-list">
              <div v-for="item in forwardTests" :key="item.window_name" class="event-item">
                <div class="row meta">
                  <strong>{{ item.window_name }}</strong>
                  <span :class="integrationClass(item.status)">{{ item.status }}</span>
                </div>
                <p>{{ item.signals_count }} sinais</p>
                <small>Win rate {{ item.win_rate }}% • score medio {{ item.average_score }}</small>
              </div>
            </div>
          </article>
        </section>

        <section id="security" class="panel-grid">
          <article class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Security</p>
                <h3>Controles, usuarios e exportacao</h3>
              </div>
              <button class="ghost-button" @click="exportCsv">Exportar CSV</button>
            </div>
            <p v-if="exportMessage" class="export-note">{{ exportMessage }}</p>
            <div class="admin-grid">
              <div class="admin-section">
                <h4>Controles</h4>
                <div class="stack">
                  <div v-for="item in securityControls" :key="item.name" class="admin-card">
                    <div class="row">
                      <strong>{{ item.name }}</strong>
                      <span :class="severityClass(item.severity)">{{ item.severity }}</span>
                    </div>
                    <p>{{ item.status }}</p>
                    <small>{{ item.details }}</small>
                  </div>
                </div>
              </div>

              <div class="admin-section">
                <h4>Usuarios</h4>
                <div class="stack">
                  <div v-for="item in users" :key="item.email" class="admin-card">
                    <div class="row">
                      <strong>{{ item.name }}</strong>
                      <span :class="integrationClass(item.status)">{{ item.status }}</span>
                    </div>
                    <p>{{ item.role }} • {{ item.email }}</p>
                    <small>2FA {{ item.two_factor_enabled ? "ativo" : "desligado" }}</small>
                  </div>
                </div>
              </div>

              <div class="admin-section">
                <h4>Alertas e scraping</h4>
                <div class="stack">
                  <div v-for="item in alertChannels" :key="item.name" class="admin-card">
                    <div class="row">
                      <strong>{{ item.name }}</strong>
                      <span :class="integrationClass(item.status)">{{ item.status }}</span>
                    </div>
                    <p>{{ item.channel_type }} • {{ item.destination }}</p>
                    <small>{{ item.notes }}</small>
                  </div>
                  <div v-for="item in scrapingSources" :key="item.name" class="admin-card">
                    <div class="row">
                      <strong>{{ item.name }}</strong>
                      <span :class="integrationClass(item.status)">{{ item.status }}</span>
                    </div>
                    <p>{{ item.scope }}</p>
                    <small>{{ item.policy }}</small>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <article class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Audit</p>
                <h3>Ultimos eventos</h3>
              </div>
            </div>
            <div class="event-list">
              <div v-for="item in audits" :key="`${item.created_at}-${item.action}`" class="event-item">
                <strong>{{ item.action }}</strong>
                <p>{{ compactDate(item.created_at) }}</p>
                <small>{{ item.details }}</small>
              </div>
            </div>
          </article>
        </section>
      </template>
    </main>

    <aside class="floating-guide" :class="`floating-guide-${floatingGuide.tone}`">
      <p class="eyebrow">Acao agora</p>
      <h3>{{ floatingGuide.title }}</h3>
      <p class="floating-subtitle">{{ floatingGuide.subtitle }}</p>
      <strong class="floating-action">{{ floatingGuide.action }}</strong>
      <ul class="floating-details">
        <li v-for="detail in floatingGuide.details" :key="detail">{{ detail }}</li>
      </ul>
    </aside>
  </div>
</template>

<style>
:root {
  color-scheme: dark;
  --panel: rgba(9, 20, 38, 0.86);
  --panel-strong: rgba(10, 25, 46, 0.98);
  --line: rgba(137, 176, 205, 0.16);
  --text: #edf5ff;
  --muted: #91a6bf;
  --cyan: #46d0d5;
  --lime: #91d971;
  --amber: #ffbb63;
  --rose: #ff7f92;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(70, 208, 213, 0.12), transparent 28%),
    radial-gradient(circle at bottom right, rgba(145, 217, 113, 0.1), transparent 22%),
    linear-gradient(180deg, #040b14 0%, #07111f 100%);
  color: var(--text);
}
a { color: inherit; text-decoration: none; }
h1, h2, h3, h4, p { margin: 0; }
.shell { min-height: 100vh; display: grid; grid-template-columns: 290px 1fr; }
.sidebar { padding: 28px; border-right: 1px solid var(--line); background: rgba(3, 9, 18, 0.82); backdrop-filter: blur(16px); display: flex; flex-direction: column; gap: 26px; }
.brand { display: grid; gap: 8px; }
.sidebar nav { display: grid; gap: 12px; }
.sidebar nav a, .sidebar-card, .panel, .metric-card, .hero-card, .state-card, .strip-panel, .floating-guide { background: var(--panel); border: 1px solid var(--line); border-radius: 24px; backdrop-filter: blur(18px); box-shadow: 0 24px 80px rgba(0, 0, 0, 0.22); }
.sidebar nav a { padding: 13px 14px; color: var(--muted); }
.sidebar nav a:hover { color: var(--text); border-color: rgba(70, 208, 213, 0.35); }
.sidebar-card { padding: 18px; display: grid; gap: 8px; }
.content { padding: 28px 28px 140px; display: grid; gap: 20px; }
.topbar, .panel-header, .row, .actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.hero-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }
.hero-card { grid-column: span 2; padding: 28px; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(140deg, rgba(70, 208, 213, 0.16), rgba(13, 25, 46, 0.94)), var(--panel-strong); }
.hero-copy { display: grid; gap: 12px; }
.chip-row { display: flex; flex-wrap: wrap; gap: 10px; }
.ghost-chip { padding: 8px 12px; border-radius: 999px; background: rgba(255,255,255,0.04); color: var(--muted); border: 1px solid var(--line); font-size: 0.82rem; }
.metric-card, .strip-panel, .panel { padding: 22px; }
.metric-card { display: grid; gap: 10px; }
.metric-card strong { font-size: 2rem; }
.score-ring { width: 116px; height: 116px; border-radius: 50%; border: 10px solid rgba(70,208,213,0.24); display: grid; place-items: center; font-size: 1.95rem; font-weight: 700; }
.command-strip, .panel-grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 18px; }
.panel.wide { min-width: 0; }
.policy-grid, .indicator-grid, .stats-grid, .admin-grid, .live-grid, .stack, .event-list { display: grid; gap: 14px; }
.policy-grid { margin-top: 18px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.chart-shell { margin-top: 16px; height: 110px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.05); background: rgba(255,255,255,0.03); padding: 10px; color: var(--cyan); }
.chart-shell.compact { height: 82px; }
.chart-shell svg { width: 100%; height: 100%; }
.live-grid { margin-top: 18px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.opportunity-card, .event-item, .admin-card { padding: 16px; border-radius: 18px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); }
.stats-grid, .indicator-grid { margin-top: 14px; grid-template-columns: repeat(2, minmax(0, 1fr)); color: var(--muted); font-size: 0.9rem; }
.opportunity-card ul, .floating-details { margin: 14px 0 0; padding-left: 18px; color: var(--muted); }
.score-bar { height: 10px; border-radius: 999px; overflow: hidden; background: rgba(255,255,255,0.06); margin-top: 14px; }
.fill { height: 100%; background: linear-gradient(90deg, var(--cyan), var(--lime)); }
.table-shell { overflow: auto; margin-top: 18px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
.row-strong { background: rgba(145,217,113,0.04); }
.row-risk { background: rgba(255,127,146,0.04); }
.decision, .badge { padding: 8px 12px; border-radius: 999px; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.buy { background: rgba(145,217,113,0.16); color: var(--lime); }
.sell { background: rgba(255,127,146,0.16); color: var(--rose); }
.neutral { background: rgba(255,187,99,0.14); color: var(--amber); }
.ghost-button, .primary-button, .market-filter { background: rgba(255,255,255,0.04); border: 1px solid var(--line); color: var(--text); border-radius: 14px; padding: 11px 14px; cursor: pointer; }
.primary-button { background: linear-gradient(90deg, rgba(70,208,213,0.18), rgba(145,217,113,0.14)); }
.primary-button:disabled { opacity: 0.65; cursor: wait; }
.state-card { padding: 28px; }
.state-card.error { border-color: rgba(255,127,146,0.35); color: var(--rose); }
.eyebrow, .muted, .hero-subtitle, .event-item p, .event-item small, .admin-card p, .admin-card small, .export-note, .panel-note, .floating-subtitle { color: var(--muted); }
.admin-grid { margin-top: 18px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.admin-section { display: grid; gap: 12px; }
.panel-note { margin-top: 16px; font-size: 0.92rem; }
.empty-state { margin-top: 18px; padding: 18px; border-radius: 18px; border: 1px dashed rgba(255,255,255,0.09); color: var(--muted); background: rgba(255,255,255,0.02); }
.floating-guide {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: min(25vw, 420px);
  min-width: 320px;
  min-height: 25vh;
  padding: 22px;
  z-index: 40;
  display: grid;
  gap: 12px;
}
.floating-guide-buy {
  background: linear-gradient(135deg, rgba(145, 217, 113, 0.22), rgba(9, 20, 38, 0.96));
  border-color: rgba(145, 217, 113, 0.34);
}
.floating-guide-sell {
  background: linear-gradient(135deg, rgba(255, 127, 146, 0.22), rgba(9, 20, 38, 0.96));
  border-color: rgba(255, 127, 146, 0.34);
}
.floating-guide-neutral {
  background: linear-gradient(135deg, rgba(255, 187, 99, 0.18), rgba(9, 20, 38, 0.96));
  border-color: rgba(255, 187, 99, 0.28);
}
.floating-action { font-size: 1.15rem; line-height: 1.4; }
@media (max-width: 1240px) {
  .shell, .hero-grid, .command-strip, .panel-grid, .admin-grid, .live-grid { grid-template-columns: 1fr; }
  .hero-card { grid-column: span 1; }
  .sidebar { border-right: 0; border-bottom: 1px solid var(--line); }
  .floating-guide { width: min(42vw, 420px); }
}
@media (max-width: 720px) {
  .content, .sidebar { padding: 18px; }
  .content { padding-bottom: 260px; }
  .topbar, .actions, .hero-card { flex-direction: column; align-items: flex-start; }
  .policy-grid, .stats-grid, .indicator-grid { grid-template-columns: 1fr; }
  .floating-guide {
    left: 16px;
    right: 16px;
    bottom: 16px;
    width: auto;
    min-width: 0;
    min-height: 0;
  }
}
</style>
