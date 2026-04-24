# Market Decision AI

Plataforma profissional de analise inteligente para trade com foco em decisao realista, risco e qualidade operacional. O projeto nasce em modo observador/simulador para validar sinais antes de qualquer automacao.

## Stack

- Backend: FastAPI + SQLAlchemy
- Frontend: Vue 3 + TypeScript + Vite
- Banco: PostgreSQL
- Fila/cache: Redis
- Infra: Docker Compose

## Modulos principais

- Dashboard SaaS com live board, score, risco, horarios operacionais e historico
- Motor de analise com score tecnico, fundamentalista e historico
- Regras de bloqueio que priorizam `NAO_OPERAR`
- API para analise de oportunidade e simulacao de snapshots
- Persistencia de candles, indicadores, sinais, resultados e logs
- Integracao publica com Binance e estrutura pronta para OANDA demo
- Base de backtest, forward test e painel administrativo

## Decisoes do motor

- `COMPRA`
- `VENDA`
- `NAO_OPERAR`

Quando a decisao for `COMPRA` ou `VENDA`, o sistema devolve tambem:

- `entry_time`
- `exit_time`
- `duration`
- `signal_valid_until`
- `duration_reason`
- `warning`

Tudo isso e apenas analitico. O sistema nao executa ordens reais nesta fase.

O score final vai de 0 a 100:

- `0-50`: nao operar
- `51-65`: fraco
- `66-75`: aceitavel
- `76-85`: forte
- `86+`: premium raro

## Roadmap implementado na arquitetura

- Coleta e persistencia de dados de mercado
- Dashboard premium de apoio operacional
- Base para backtest, forward test e aprendizado continuo
- Estrutura pronta para integrar APIs oficiais, scraping publico permitido e modelos de ML

## Como rodar com Docker

```bash
docker compose up --build
```

Servicos:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Docs da API: `http://localhost:8000/docs`

## Variaveis de ambiente

Veja [.env.example](C:/Users/junin/OneDrive/Documentos/New%20project/.env.example).

Credenciais opcionais para preparacao oficial:

- `OANDA_API_KEY`
- `OANDA_ACCOUNT_ID`
- `OANDA_BASE_URL`

## Proximos passos recomendados

1. Conectar fontes oficiais como Binance, OANDA, Finnhub ou Twelve Data.
2. Adicionar workers para ingestao continua e scraping publico permitido.
3. Implementar backtest de 3 anos por ativo/timeframe.
4. Validar 30 dias de forward test com no minimo 500 sinais.
5. Incluir autenticacao, RBAC e criptografia de chaves API.
