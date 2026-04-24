<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "./api";
import type {
  BacktestMetricItem,
  DashboardPayload,
  EconomicEventItem,
  ForwardTestMetricItem,
  LiveAssetBoardItem,
  SignalItem
} from "./types";

const loading = ref(true);
const error = ref("");
const refreshingLive = ref(false);
const dashboard = ref<DashboardPayload | null>(null);
const selectedMarket = ref("TODOS");

const summary = computed(() => dashboard.value?.summary ?? null);
const signals = computed(() => dashboard.value?.signals ?? []);
const events = computed(() => dashboard.value?.economic_events ?? []);
const liveBoard = computed(() => dashboard.value?.live_board ?? []);
const opportunities = computed(() => dashboard.value?.opportunities ?? []);
const integrations = computed(() => dashboard.value?.integrations ?? []);
const monitoredAssets = computed(() => dashboard.value?.monitored_assets ?? []);
const modules = computed(() => dashboard.value?.modules ?? []);
const riskProfile = computed(() => dashboard.value?.risk_profile ?? null);
const backtests = computed(() => dashboard.value?.backtests ?? []);
const forwardTests = computed(() => dashboard.value?.forward_tests ?? []);
const audits = computed(() => dashboard.value?.audits ?? []);

const filteredSignals = computed(() =>
  selectedMarket.value === "TODOS"
    ? signals.value
    : signals.value.filter((signal) => signal.market === selectedMarket.value)
);

const headline = computed(() => liveBoard.value[0] ?? opportunities.value[0] ?? null);

const qualityStrip = computed(() =>
  liveBoard.value.slice(0, 4).map((item) => ({
    symbol: item.symbol,
    score: item.score
  }))
);

const topBacktest = computed(() => backtests.value[0] ?? null);
const topForward = computed(() => forwardTests.value[0] ?? null);

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
  refreshingLive.value = true;
  error.value = "";
  try {
    const board = await api.refreshLiveBoard();
    if (dashboard.value) {
      dashboard.value = {
        ...dashboard.value,
        live_board: board
      };
    } else {
      await loadDashboard();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Falha ao atualizar a varredura";
  } finally {
    refreshingLive.value = false;
  }
}

onMounted(loadDashboard);

function decisionClass(decision: string) {
  return {
    COMPRA: "decision buy",
    VENDA: "decision sell",
    NAO_OPERAR: "decision neutral"
  }[decision] ?? "decision neutral";
}

function impactClass(impact: string) {
  return {
    ALTO: "impact high",
    MEDIO: "impact medium",
    BAIXO: "impact low"
  }[impact] ?? "impact low";
}

function integrationClass(status: string) {
  return {
    ativo: "decision buy",
    observador: "decision neutral",
    "aguardando-chave": "decision neutral",
    disabled: "decision sell"
  }[status] ?? "decision neutral";
}

function moduleClass(enabled: boolean, mode: string) {
  if (!enabled || mode === "disabled") return "decision sell";
  if (mode === "observer") return "decision neutral";
  return "decision buy";
}

function scoreRailStyle(score: number) {
  return { width: `${Math.max(8, Math.min(score, 100))}%` };
}

function compactDate(value: string) {
  return new Date(value).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
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
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <p class="eyebrow">Trade Intelligence</p>
        <h1>Ops Deck</h1>
        <span class="muted">Modo observador com foco em qualidade, risco e auditoria.</span>
      </div>

      <nav>
        <a href="#command">Command</a>
        <a href="#live-board">Live Board</a>
        <a href="#signals">Signals</a>
        <a href="#macro">Macro</a>
        <a href="#lab">Lab</a>
        <a href="#admin">Admin</a>
      </nav>

      <div class="sidebar-card">
        <p class="muted">Politica operacional</p>
        <strong>Nunca forcar entrada</strong>
        <span>Resposta valida inclui sempre `NAO_OPERAR`. IQ Option ou qualquer corretora deve ficar fora de automacao cega.</span>
      </div>
    </aside>

    <main class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">Central de decisao</p>
          <h2>Analise estatistica, macro e tecnica em uma camada unica</h2>
        </div>
        <div class="actions">
          <button class="ghost-button" @click="loadDashboard">Recarregar</button>
          <button class="primary-button" :disabled="refreshingLive" @click="refreshLiveBoard">
            {{ refreshingLive ? "Varrendo..." : "Executar varredura ao vivo" }}
          </button>
        </div>
      </header>

      <section v-if="loading" class="state-card">Carregando command center...</section>
      <section v-else-if="error" class="state-card error">{{ error }}</section>

      <template v-else-if="dashboard && summary && riskProfile">
        <section id="command" class="hero-grid">
          <article class="hero-card">
            <div class="hero-copy">
              <p class="eyebrow">Leitura lider</p>
              <h3>{{ headline?.decision ?? "NAO_OPERAR" }}</h3>
              <p class="hero-subtitle">
                {{ headline?.symbol ?? "Aguardando varredura" }} • score {{ headline?.score ?? 0 }} • risco {{ headline?.risk_level ?? "Alto" }}
              </p>
              <div class="chip-row">
                <span class="ghost-chip">Melhor ativo: {{ summary.best_symbol }}</span>
                <span class="ghost-chip">Melhor timeframe: {{ summary.best_timeframe }}</span>
                <span class="ghost-chip">Observer mode: {{ riskProfile.observer_mode ? "ON" : "OFF" }}</span>
              </div>
            </div>
            <div class="score-ring">
              <span>{{ Math.round(headline?.score ?? 0) }}</span>
            </div>
          </article>

          <article class="metric-card">
            <span>Total de sinais</span>
            <strong>{{ summary.total_signals }}</strong>
            <small class="muted">Compra {{ summary.buy_signals }} • Venda {{ summary.sell_signals }} • Nao operar {{ summary.no_trade_signals }}</small>
          </article>
          <article class="metric-card">
            <span>Win rate fechado</span>
            <strong>{{ summary.win_rate }}%</strong>
            <small class="muted">Apenas sinais com resultado conhecido entram no calculo.</small>
          </article>
          <article class="metric-card">
            <span>Alertas macro</span>
            <strong>{{ summary.active_alerts }}</strong>
            <small class="muted">Eventos publicos mapeados para filtro operacional.</small>
          </article>
          <article class="metric-card">
            <span>Premium raro</span>
            <strong>{{ summary.premium_opportunities }}</strong>
            <small class="muted">Pontuacoes acima de 86 sao escassas por desenho.</small>
          </article>
        </section>

        <section class="command-strip">
          <div class="strip-panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Pulse</p>
                <h3>Distribuicao de score</h3>
              </div>
            </div>
            <div class="quality-strip">
              <div v-for="item in qualityStrip" :key="item.symbol" class="quality-card">
                <span>{{ item.symbol }}</span>
                <div class="mini-rail">
                  <div class="mini-fill" :style="scoreRailStyle(item.score)"></div>
                </div>
                <strong>{{ item.score }}</strong>
              </div>
            </div>
          </div>

          <div class="strip-panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Risk posture</p>
                <h3>Politica ativa</h3>
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
                <h3>Varredura multiativo em tempo real</h3>
              </div>
              <div class="badge">Apoio operacional. Nao executa ordens.</div>
            </div>

            <div class="live-grid">
              <article v-for="item in liveBoard" :key="`${item.symbol}-${item.timeframe}`" class="opportunity-card">
                <div class="row">
                  <div>
                    <strong>{{ item.symbol }}</strong>
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
                  <span>Tendencia {{ item.trend }}</span>
                  <span>Vol {{ item.volatility }}%</span>
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

                <p v-if="item.blockers.length" class="blockers">Bloqueios: {{ item.blockers.join(" • ") }}</p>
              </article>
            </div>
          </article>

          <article id="macro" class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Macro</p>
                <h3>Calendario e sentimento</h3>
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

        <section id="signals" class="panel-grid lower">
          <article class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Execution journal</p>
                <h3>Historico de sinais</h3>
              </div>
              <select v-model="selectedMarket" class="market-filter">
                <option value="TODOS">Todos</option>
                <option value="FOREX">Forex</option>
                <option value="CRYPTO">Cripto</option>
              </select>
            </div>
            <div class="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Ativo</th>
                    <th>Mercado</th>
                    <th>TF</th>
                    <th>Decisao</th>
                    <th>Score</th>
                    <th>Risco</th>
                    <th>Leitura</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="signal in filteredSignals" :key="signal.id" :class="rowClass(signal.score)">
                    <td>{{ compactDate(signal.timestamp) }}</td>
                    <td>{{ signal.symbol }}</td>
                    <td>{{ signal.market }}</td>
                    <td>{{ signal.timeframe }}</td>
                    <td><span :class="decisionClass(signal.decision)">{{ signal.decision }}</span></td>
                    <td>{{ signal.score }}</td>
                    <td>{{ signal.risk_level }}</td>
                    <td>{{ reasonsText(signal) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <article id="lab" class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Lab</p>
                <h3>Backtest e forward test</h3>
              </div>
            </div>
            <div class="lab-stack">
              <div class="lab-card" v-if="topBacktest">
                <p class="muted">Melhor backtest</p>
                <strong>{{ topBacktest.strategy_name }}</strong>
                <small>{{ topBacktest.symbol }} • {{ topBacktest.timeframe }} • win rate {{ topBacktest.win_rate }}% • payoff {{ topBacktest.payoff }}</small>
              </div>
              <div class="lab-card" v-if="topForward">
                <p class="muted">Forward test</p>
                <strong>{{ topForward.window_name }}</strong>
                <small>{{ topForward.signals_count }} sinais • score medio {{ topForward.average_score }} • {{ topForward.status }}</small>
              </div>
              <div class="lab-card">
                <p class="muted">Principio</p>
                <strong>Sem robo milagroso</strong>
                <small>Qualidade de entrada, bloqueio de contexto ruim e auditoria acima de volume de sinal.</small>
              </div>
            </div>
          </article>
        </section>

        <section class="panel-grid lower">
          <article class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Strategy Lab</p>
                <h3>Backtests por estrategia</h3>
              </div>
            </div>
            <div class="backtest-grid">
              <div v-for="item in backtests" :key="`${item.strategy_name}-${item.symbol}`" class="lab-metric">
                <strong>{{ item.strategy_name }}</strong>
                <p>{{ item.symbol }} • {{ item.timeframe }}</p>
                <div class="stats-grid">
                  <span>Win rate {{ item.win_rate }}%</span>
                  <span>Payoff {{ item.payoff }}</span>
                  <span>Drawdown {{ item.drawdown }}%</span>
                  <span>Lucro {{ item.net_profit }}R</span>
                  <span>Pior sequencia {{ item.worst_streak }}</span>
                  <span>Melhor hora {{ item.best_hour }}</span>
                </div>
              </div>
            </div>
          </article>

          <article class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Forward</p>
                <h3>Paper trade</h3>
              </div>
            </div>
            <div class="event-list">
              <div v-for="item in forwardTests" :key="item.window_name" class="event-item">
                <div class="row meta">
                  <strong>{{ item.window_name }}</strong>
                  <span :class="integrationClass(item.status)">{{ item.status }}</span>
                </div>
                <p>{{ item.signals_count }} sinais • win rate {{ item.win_rate }}%</p>
                <small>{{ item.notes }}</small>
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
                      <strong>{{ item.symbol }}</strong>
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
                <p class="eyebrow">Audit</p>
                <h3>Ultimos eventos</h3>
              </div>
            </div>
            <div class="event-list">
              <div v-for="item in audits" :key="`${item.created_at}-${item.action}`" class="event-item">
                <div class="row meta">
                  <strong>{{ item.action }}</strong>
                  <span class="badge">{{ item.actor }}</span>
                </div>
                <p>{{ compactDate(item.created_at) }}</p>
                <small>{{ item.details }}</small>
              </div>
            </div>
          </article>
        </section>
      </template>
    </main>
  </div>
</template>

<style>
:root {
  color-scheme: dark;
  --bg: #06101c;
  --bg-soft: #0f1b2d;
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

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(70, 208, 213, 0.12), transparent 28%),
    radial-gradient(circle at bottom right, rgba(145, 217, 113, 0.1), transparent 22%),
    linear-gradient(180deg, #040b14 0%, #07111f 100%);
  color: var(--text);
}

a {
  color: inherit;
  text-decoration: none;
}

h1,
h2,
h3,
h4,
p {
  margin: 0;
}

.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 290px 1fr;
}

.sidebar {
  padding: 28px;
  border-right: 1px solid var(--line);
  background: rgba(3, 9, 18, 0.82);
  backdrop-filter: blur(16px);
  display: flex;
  flex-direction: column;
  gap: 26px;
}

.brand {
  display: grid;
  gap: 8px;
}

.sidebar nav {
  display: grid;
  gap: 12px;
}

.sidebar nav a,
.sidebar-card,
.panel,
.metric-card,
.hero-card,
.state-card,
.strip-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.22);
}

.sidebar nav a {
  padding: 13px 14px;
  color: var(--muted);
}

.sidebar nav a:hover {
  color: var(--text);
  border-color: rgba(70, 208, 213, 0.35);
}

.sidebar-card {
  padding: 18px;
  display: grid;
  gap: 8px;
}

.content {
  padding: 28px;
  display: grid;
  gap: 20px;
}

.topbar,
.panel-header,
.row,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.hero-card {
  grid-column: span 2;
  padding: 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background:
    linear-gradient(140deg, rgba(70, 208, 213, 0.16), rgba(13, 25, 46, 0.94)),
    var(--panel-strong);
}

.hero-copy {
  display: grid;
  gap: 12px;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.ghost-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--muted);
  border: 1px solid var(--line);
  font-size: 0.82rem;
}

.metric-card,
.strip-panel,
.panel {
  padding: 22px;
}

.metric-card {
  display: grid;
  gap: 10px;
}

.metric-card strong {
  font-size: 2rem;
}

.score-ring {
  width: 116px;
  height: 116px;
  border-radius: 50%;
  border: 10px solid rgba(70, 208, 213, 0.24);
  display: grid;
  place-items: center;
  font-size: 1.95rem;
  font-weight: 700;
}

.command-strip,
.panel-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 18px;
}

.panel.wide {
  min-width: 0;
}

.quality-strip,
.policy-grid,
.indicator-grid,
.stats-grid,
.admin-grid,
.live-grid,
.backtest-grid,
.stack,
.event-list,
.lab-stack {
  display: grid;
  gap: 14px;
}

.quality-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 18px;
}

.quality-card,
.opportunity-card,
.event-item,
.lab-card,
.lab-metric,
.admin-card {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.quality-card {
  display: grid;
  gap: 8px;
}

.policy-grid {
  margin-top: 18px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel-grid .panel {
  min-height: 100%;
}

.live-grid {
  margin-top: 18px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.stats-grid,
.indicator-grid {
  margin-top: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  color: var(--muted);
  font-size: 0.9rem;
}

.opportunity-card ul {
  margin: 14px 0 0;
  padding-left: 18px;
  color: var(--muted);
}

.blockers {
  margin-top: 12px;
  color: var(--amber);
  font-size: 0.92rem;
}

.score-bar,
.mini-rail {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
  margin-top: 14px;
}

.mini-rail {
  margin-top: 0;
  height: 8px;
}

.fill,
.mini-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--cyan), var(--lime));
}

.table-shell {
  overflow: auto;
  margin-top: 18px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 12px 8px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}

.row-strong {
  background: rgba(145, 217, 113, 0.04);
}

.row-risk {
  background: rgba(255, 127, 146, 0.04);
}

.decision,
.impact,
.badge {
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.buy {
  background: rgba(145, 217, 113, 0.16);
  color: var(--lime);
}

.sell {
  background: rgba(255, 127, 146, 0.16);
  color: var(--rose);
}

.neutral,
.low {
  background: rgba(255, 187, 99, 0.14);
  color: var(--amber);
}

.high {
  background: rgba(255, 127, 146, 0.16);
  color: var(--rose);
}

.medium {
  background: rgba(70, 208, 213, 0.16);
  color: var(--cyan);
}

.badge,
.ghost-button,
.primary-button,
.market-filter {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--line);
  color: var(--text);
}

.ghost-button,
.primary-button,
.market-filter {
  border-radius: 14px;
  padding: 11px 14px;
  cursor: pointer;
}

.primary-button {
  background: linear-gradient(90deg, rgba(70, 208, 213, 0.18), rgba(145, 217, 113, 0.14));
}

.primary-button:disabled {
  opacity: 0.65;
  cursor: wait;
}

.state-card {
  padding: 28px;
}

.state-card.error {
  border-color: rgba(255, 127, 146, 0.35);
  color: var(--rose);
}

.eyebrow,
.muted,
.hero-subtitle,
.event-item p,
.event-item small,
.lab-card small,
.lab-metric p,
.admin-card p,
.admin-card small {
  color: var(--muted);
}

.admin-grid {
  margin-top: 18px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.admin-section {
  display: grid;
  gap: 12px;
}

@media (max-width: 1240px) {
  .shell,
  .hero-grid,
  .command-strip,
  .panel-grid,
  .admin-grid,
  .quality-strip,
  .live-grid {
    grid-template-columns: 1fr;
  }

  .hero-card {
    grid-column: span 1;
  }

  .sidebar {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
}

@media (max-width: 720px) {
  .content,
  .sidebar {
    padding: 18px;
  }

  .topbar,
  .actions,
  .hero-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .policy-grid,
  .stats-grid,
  .indicator-grid {
    grid-template-columns: 1fr;
  }
}
</style>
