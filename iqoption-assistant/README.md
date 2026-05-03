# iqoption-assistant

Assistente local em Python para abrir/controlar o Google Chrome, preparar a tela da IQ Option e operar somente com protecoes fortes. Por padrao o projeto roda em observacao (`DRY_RUN=true`).

## Garantias de seguranca

- Nunca executa compra/venda automaticamente em conta real.
- `DRY_RUN=true` por padrao.
- Nunca altera valor de entrada automaticamente. Usa apenas o valor que ja estiver definido manualmente na tela.
- Nao faz login, nao captura senha e nao salva credenciais.
- Se a IQ Option exigir login, a automacao pausa e pede login manual.
- So existe caminho de clique experimental se:
  - `DRY_RUN=false`
  - `DEMO_ONLY=true`
  - `ALLOW_AUTO_CLICK=true`
  - a flag `--allow-click-demo-only` for usada
  - a conta aparentar ser DEMO
  - a sessao estiver armada com `ARMAR MODO DEMO`

## Estrutura

```text
iqoption-assistant/
  README.md
  requirements.txt
  .env.example
  main.py
  config.py
  signal_parser.py
  browser_controller.py
  auto_trader.py
  floating_stop.py
  risk_guard.py
  storage/
    logs/
  tests/
```

## Instalacao

```powershell
cd iqoption-assistant
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chrome
```

## Configuracao

Crie um arquivo `.env` a partir de `.env.example`.

Exemplo seguro:

```env
DRY_RUN=true
DEMO_ONLY=true
ALLOW_AUTO_CLICK=false
SESSION_ARM_REQUIRED=true
MAX_TRADES_PER_SESSION=5
MAX_DAILY_LOSS=0
STOP_FILE=storage/STOP_TRADING.flag
IQ_OPTION_URL=https://iqoption.com/traderoom
CHROME_DEBUG_PORT=9222
CHROME_USER_DATA_DIR=.chrome-profile
LOGIN_WAIT_TIMEOUT_SECONDS=600
ALERT_BEFORE_SECONDS=10
LOG_LEVEL=INFO
```

## Uso

```powershell
python main.py
```

Ou com parametros:

```powershell
python main.py --ativo EUR/USD --direcao COMPRA --horario 14:35 --expiracao M1
```

Modo experimental para DEMO somente:

```powershell
python main.py --ativo EUR/USD --direcao COMPRA --horario 14:35 --expiracao M1 --allow-click-demo-only
```

Tambem aceita sinal em linha unica:

```powershell
python main.py --signal-text "ativo=EUR/USD | direcao=VENDA | horario=14:35 | expiracao=M1"
```

## Modos

- `DRY_RUN`: apenas alerta e destaca qual botao deve ser clicado manualmente.
- `DEMO_ARMADO`: permite clique automatico apenas em demo, se todos os guardas passarem.
- `STOP`: bloqueia tudo imediatamente, cria `storage/STOP_TRADING.flag` e desarma a sessao.

## Fluxo esperado

1. Verifica se o Chrome esta aberto.
2. Se houver Chrome controlavel com porta de depuracao, conecta.
3. Se nao houver, abre uma instancia controlada do Chrome.
4. Acessa `https://iqoption.com/traderoom`.
5. Se houver login pendente, pausa para login manual.
6. Tenta preparar a selecao do ativo informado.
7. Mostra botao STOP flutuante sempre visivel e registra hotkey `CTRL + SHIFT + S`.
8. Mostra confirmacao:
   - `Confirmar entrada? ativo=X direcao=Y horario=Z expiracao=W`
9. Dispara alerta 10 segundos antes.
10. No horario exato:
   - em `dry-run`: apenas destaca o botao e orienta clique manual
   - em demo armado: so clica se todos os guardas passarem

## Armando a sessao DEMO

Quando o programa iniciar, ele pode pedir:

```text
ARMAR MODO DEMO
```

Somente depois disso a sessao fica armada para auto-click em demo. A sessao desarma automaticamente se:

- o usuario clicar em `STOP`
- a hotkey `CTRL + SHIFT + S` for pressionada
- atingir o limite de operacoes
- houver erro
- o navegador fechar
- o ativo mudar inesperadamente
- o horario do sinal expirar

## Logs

Os logs sao gravados em:

```text
storage/logs/trading-assistant.log
```

## Testes

```powershell
python -m pytest
```

## Limitacoes conhecidas

- A IQ Option pode mudar seletores e textos da interface.
- A automacao tenta localizar campos de busca e botoes conhecidos, mas pode precisar de ajuste fino visual.
- O projeto nao promete lucro, nao calcula martingale e nao substitui decisao humana.
- `MAX_DAILY_LOSS` fica reservado para integracao futura com leitura de resultado; nesta fase ele nao recalcula perdas automaticamente.
