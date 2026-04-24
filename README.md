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
- Motor de analise com engines separados: tecnico, fundamentalista, historico, validacao, timing e scoring
- Regras de bloqueio que priorizam `NAO_OPERAR`
- API para analise de oportunidade e simulacao de snapshots
- Persistencia de candles, indicadores, sinais, resultados e logs
- Integracao publica com Binance e estrutura pronta para OANDA demo
- Base de backtest, forward test, painel administrativo e streaming live via WebSocket
- Worker continuo com Redis para coleta de mercado, macro e atualizacao de relatorios

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
- WebSocket live board: `ws://localhost:8000/api/v1/market/live-board/ws`

## Producao em hospedagem compartilhada

O frontend aceita URL configuravel por ambiente:

- `VITE_API_BASE`
- `VITE_WS_BASE`

Exemplo em [frontend/.env.production.example](</C:/Users/junin/OneDrive/Documentos/New project/frontend/.env.production.example>).

O backend agora tambem aceita MySQL/MariaDB via SQLAlchemy:

- `mysql+pymysql://USER:PASSWORD@localhost/DATABASE_NAME`

Exemplo em [backend/.env.production.example](</C:/Users/junin/OneDrive/Documentos/New project/backend/.env.production.example>).

Para hospedagem Python estilo cPanel/Passenger, o entrypoint esta em [backend/passenger_wsgi.py](</C:/Users/junin/OneDrive/Documentos/New project/backend/passenger_wsgi.py>).

Script de publicacao do frontend:

- [scripts/deploy_frontend.ps1](</C:/Users/junin/OneDrive/Documentos/New project/scripts/deploy_frontend.ps1>)

## Variaveis de ambiente

Veja [.env.example](C:/Users/junin/OneDrive/Documentos/New%20project/.env.example).

Credenciais opcionais para preparacao oficial:

- `OANDA_API_KEY`
- `OANDA_ACCOUNT_ID`
- `OANDA_BASE_URL`

Credenciais estruturais:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `API_ADMIN_TOKEN`
- `API_ANALYST_TOKEN`

## Arquitetura profissional adicionada

- `backend/app/services/engines/`
- `backend/app/services/backtest.py`
- `backend/app/services/forward_test.py`
- `backend/app/services/live_feed.py`
- `backend/app/workers/collector.py`
- `backend/app/workers/macro.py`
- `backend/app/db/migrations/001_market_decision_ai.sql`

## Endpoints novos

- `GET /api/v1/health/detailed`
- `POST /api/v1/backtest/run`
- `POST /api/v1/forward-test/evaluate`
- `WS /api/v1/market/live-board/ws`

## Proximos passos recomendados

1. Conectar mais fontes oficiais como Finnhub ou Twelve Data.
2. Trocar o scraper sintetico por conectores publicos reais de calendario e noticias.
3. Adicionar autenticacao, RBAC completo e 2FA real.
4. Expandir o replay para 3 anos de historico por ativo/timeframe.
5. Incluir ML adaptativo somente depois da validacao estatistica.
