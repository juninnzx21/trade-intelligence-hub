<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "./api";
import type { DashboardSummary, EconomicEventItem, OpportunityCard, SignalItem } from "./types";

const loading = ref(true);
const error = ref("");
const summary = ref<DashboardSummary | null>(null);
const signals = ref<SignalItem[]>([]);
const opportunities = ref<OpportunityCard[]>([]);
const events = ref<EconomicEventItem[]>([]);
const selectedMarket = ref("TODOS");

const filteredSignals = computed(() =>
  selectedMarket.value === "TODOS"
    ? signals.value
    : signals.value.filter((signal) => signal.market === selectedMarket.value)
);

const heroDecision = computed(() => opportunities.value[0]?.decision ?? "NAO_OPERAR");
const heroSymbol = computed(() => opportunities.value[0]?.symbol ?? "Aguardando");
const heroScore = computed(() => opportunities.value[0]?.score ?? 0);

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [summaryData, signalsData, opportunitiesData, eventsData] = await Promise.all([
      api.getSummary(),
      api.getSignals(),
      api.getOpportunities(),
      api.getEconomicEvents()
    ]);
    summary.value = summaryData;
    signals.value = signalsData;
    opportunities.value = opportunitiesData;
    events.value = eventsData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Falha ao carregar dashboard";
  } finally {
    loading.value = false;
  }
};

onMounted(load);

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
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">Trade Intelligence</p>
        <h1>Hub</h1>
      </div>
      <nav>
        <a href="#overview">Overview</a>
        <a href="#opportunities">Oportunidades</a>
        <a href="#signals">Sinais</a>
        <a href="#macro">Macro</a>
        <a href="#risk">Risco</a>
      </nav>
      <div class="sidebar-card">
        <p class="muted">Modo do sistema</p>
        <strong>Observador / Simulador</strong>
        <span>Sem automacao direta. Foco em validacao realista.</span>
      </div>
    </aside>

    <main class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">Central de decisao</p>
          <h2>Analise operacional premium</h2>
        </div>
        <button class="refresh" @click="load">Atualizar dados</button>
      </header>

      <section v-if="loading" class="state-card">Carregando inteligencia operacional...</section>
      <section v-else-if="error" class="state-card error">{{ error }}</section>

      <template v-else-if="summary">
        <section id="overview" class="hero-grid">
          <article class="hero-card">
            <div class="hero-copy">
              <p class="eyebrow">Melhor leitura atual</p>
              <h3>{{ heroDecision }}</h3>
              <p class="hero-subtitle">{{ heroSymbol }} com score {{ heroScore }}</p>
            </div>
            <div class="score-ring">
              <span>{{ heroScore }}</span>
            </div>
          </article>

          <article class="metric-card">
            <span>Total de sinais</span>
            <strong>{{ summary.total_signals }}</strong>
          </article>
          <article class="metric-card">
            <span>Win rate</span>
            <strong>{{ summary.win_rate }}%</strong>
          </article>
          <article class="metric-card">
            <span>Alertas macro</span>
            <strong>{{ summary.active_alerts }}</strong>
          </article>
          <article class="metric-card">
            <span>Oportunidades premium</span>
            <strong>{{ summary.premium_opportunities }}</strong>
          </article>
        </section>

        <section class="panel-grid">
          <article id="opportunities" class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Radar</p>
                <h3>Oportunidades por score</h3>
              </div>
              <div class="badge">Melhor ativo: {{ summary.best_symbol }}</div>
            </div>
            <div class="opportunity-list">
              <div v-for="item in opportunities" :key="`${item.symbol}-${item.timeframe}`" class="opportunity-card">
                <div class="row">
                  <div>
                    <strong>{{ item.symbol }}</strong>
                    <p>{{ item.market }} • {{ item.timeframe }} • {{ item.trend }}</p>
                  </div>
                  <span :class="decisionClass(item.decision)">{{ item.decision }}</span>
                </div>
                <div class="score-bar">
                  <div class="fill" :style="{ width: `${item.score}%` }"></div>
                </div>
                <div class="row meta">
                  <span>Score {{ item.score }}</span>
                  <span>Risco {{ item.risk_level }}</span>
                </div>
                <ul>
                  <li v-for="reason in item.reasons" :key="reason">{{ reason }}</li>
                </ul>
              </div>
            </div>
          </article>

          <article id="macro" class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Macro</p>
                <h3>Agenda economica</h3>
              </div>
            </div>
            <div class="event-list">
              <div v-for="event in events" :key="`${event.title}-${event.event_time}`" class="event-item">
                <div class="row meta">
                  <strong>{{ event.title }}</strong>
                  <span :class="impactClass(event.impact)">{{ event.impact }}</span>
                </div>
                <p>{{ event.region }} • {{ new Date(event.event_time).toLocaleString("pt-BR") }}</p>
                <small>{{ event.summary }}</small>
              </div>
            </div>
          </article>
        </section>

        <section class="panel-grid lower">
          <article id="signals" class="panel wide">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Historico</p>
                <h3>Sinais registrados</h3>
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
                    <th>Ativo</th>
                    <th>Mercado</th>
                    <th>TF</th>
                    <th>Decisao</th>
                    <th>Score</th>
                    <th>Risco</th>
                    <th>Tendencia</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="signal in filteredSignals" :key="signal.id">
                    <td>{{ signal.symbol }}</td>
                    <td>{{ signal.market }}</td>
                    <td>{{ signal.timeframe }}</td>
                    <td><span :class="decisionClass(signal.decision)">{{ signal.decision }}</span></td>
                    <td>{{ signal.score }}</td>
                    <td>{{ signal.risk_level }}</td>
                    <td>{{ signal.trend }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <article id="risk" class="panel">
            <div class="panel-header">
              <div>
                <p class="eyebrow">Disciplina</p>
                <h3>Governanca de risco</h3>
              </div>
            </div>
            <div class="risk-stack">
              <div class="risk-rule">
                <strong>Bloqueios ativos</strong>
                <p>Noticia forte, spread elevado, lateralizacao extrema e candle esticado travam entrada.</p>
              </div>
              <div class="risk-rule">
                <strong>Gestao futura</strong>
                <p>Stake configuravel, stop diario, pausa automatica e reducao de exposicao apos perdas.</p>
              </div>
              <div class="risk-rule">
                <strong>Aprendizado continuo</strong>
                <p>Todo sinal deve registrar contexto, decisao e resultado posterior para evolucao estatistica.</p>
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
  --bg: #07111f;
  --bg-soft: #0f1d31;
  --panel: rgba(8, 21, 39, 0.84);
  --panel-strong: rgba(13, 29, 52, 0.96);
  --line: rgba(142, 176, 212, 0.18);
  --text: #e6edf7;
  --muted: #90a7c4;
  --cyan: #37d4d9;
  --lime: #8edb72;
  --amber: #ffbf5f;
  --rose: #ff7d8e;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(55, 212, 217, 0.12), transparent 30%),
    radial-gradient(circle at top right, rgba(142, 219, 114, 0.1), transparent 25%),
    linear-gradient(180deg, #07111f 0%, #020812 100%);
  color: var(--text);
}

a {
  color: inherit;
  text-decoration: none;
}

.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px 1fr;
}

.sidebar {
  padding: 28px;
  border-right: 1px solid var(--line);
  background: rgba(2, 8, 18, 0.72);
  backdrop-filter: blur(16px);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 24px;
}

.sidebar nav {
  display: grid;
  gap: 12px;
}

.sidebar nav a {
  padding: 12px 14px;
  border: 1px solid transparent;
  border-radius: 14px;
  color: var(--muted);
  background: rgba(255, 255, 255, 0.02);
}

.sidebar nav a:hover {
  border-color: var(--line);
  color: var(--text);
}

.sidebar-card,
.panel,
.metric-card,
.hero-card,
.state-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  backdrop-filter: blur(16px);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.18);
}

.sidebar-card {
  padding: 18px;
  display: grid;
  gap: 8px;
}

.content {
  padding: 28px;
  display: grid;
  gap: 24px;
}

.topbar,
.panel-header,
.row {
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
  background:
    linear-gradient(135deg, rgba(55, 212, 217, 0.16), rgba(10, 22, 40, 0.9)),
    var(--panel-strong);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-card {
  padding: 24px;
  display: grid;
  gap: 10px;
}

.metric-card strong {
  font-size: 2rem;
}

.score-ring {
  width: 112px;
  height: 112px;
  border-radius: 50%;
  border: 10px solid rgba(55, 212, 217, 0.24);
  display: grid;
  place-items: center;
  font-size: 1.9rem;
  font-weight: 700;
}

.panel-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 18px;
}

.panel {
  padding: 22px;
}

.panel.wide {
  min-width: 0;
}

.opportunity-list,
.event-list,
.risk-stack {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.opportunity-card,
.event-item,
.risk-rule {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.opportunity-card ul {
  margin: 12px 0 0;
  padding-left: 18px;
  color: var(--muted);
}

.score-bar {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
  margin-top: 14px;
}

.fill {
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
}

.decision,
.impact,
.badge {
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.buy {
  background: rgba(142, 219, 114, 0.16);
  color: var(--lime);
}

.sell {
  background: rgba(255, 125, 142, 0.16);
  color: var(--rose);
}

.neutral,
.low {
  background: rgba(255, 191, 95, 0.14);
  color: var(--amber);
}

.high {
  background: rgba(255, 125, 142, 0.16);
  color: var(--rose);
}

.medium {
  background: rgba(55, 212, 217, 0.16);
  color: var(--cyan);
}

.badge,
.refresh,
.market-filter {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--line);
  color: var(--text);
}

.refresh,
.market-filter {
  border-radius: 14px;
  padding: 11px 14px;
}

.eyebrow,
.muted,
.hero-subtitle,
.event-item p,
.risk-rule p,
.sidebar-card span,
.meta {
  color: var(--muted);
}

.state-card {
  padding: 28px;
}

.state-card.error {
  border-color: rgba(255, 125, 142, 0.35);
  color: var(--rose);
}

h1,
h2,
h3,
p {
  margin: 0;
}

@media (max-width: 1120px) {
  .shell,
  .panel-grid,
  .hero-grid {
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

  .hero-card {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
