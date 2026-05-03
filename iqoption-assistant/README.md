# iqoption-assistant

Assistente local em Python para abrir/controlar o Google Chrome, preparar a tela da IQ Option e operar somente com protecoes fortes. Por padrao o projeto roda em observacao (`DRY_RUN=true`).

## Garantias de seguranca

- Nunca executa compra/venda automaticamente em conta real.
- `DRY_RUN=true` por padrao.
- Nunca altera valor de entrada automaticamente. Usa apenas o valor que ja estiver definido manualmente na tela.
- Nao faz login, nao captura senha e nao salva credenciais.
- Se a IQ Option exigir login, a automacao pausa e pede login manual.
- O app sempre inicia em `PARADO`.
- So existe caminho de clique experimental se:
  - `DRY_RUN=false`
  - `DEMO_ONLY=true`
  - `ALLOW_AUTO_CLICK=true`
  - a flag `--allow-click-demo-only` for usada
  - a conta aparentar ser DEMO
  - a sessao estiver armada manualmente com `START`
- Antes de qualquer `START`, o app exige:
  - PIN local validado
  - integridade local aprovada
  - `STOP_TRADING.flag` inexistente
  - conta DEMO confirmada
- Auditoria local pode ser cifrada em repouso com `ASSISTANT_MASTER_KEY`.
- Logs aplicam redacao basica para evitar vazamento acidental de segredos no terminal.
- Esta protecao e local. Ela nao serve para esconder automacao da plataforma nem para burlar deteccao.

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
  risk_guard.py
  pin_guard.py
  integrity_guard.py
  audit_exporter.py
  ui/
    app.py
    controller.py
    main_window.py
    theme.py
    widgets/
  build_windows.ps1
  iqoption-assistant.spec
  requirements-dev.txt
  storage/
    logs/
  tests/
```

## Instalacao

```powershell
cd "C:\Users\junin\OneDrive\Documentos\New project\iqoption-assistant"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chrome
```

## Configuracao

Crie um arquivo `.env` a partir de `.env.example`.

Exemplo seguro:

```env
ASSISTANT_PIN=12345690
ENABLE_LOCAL_ENCRYPTION=true
ASSISTANT_MASTER_KEY=8Kf9xQ2wVvL1nT7yZcR4pM6bH3sXjE9aD5uN0kGqYhU=
ENCRYPTED_AUDIT_FILE=storage/logs/audit.secure.log
INTEGRITY_MANIFEST=storage/integrity_manifest.json
PIN_HASH_FILE=storage/pin.hash
PIN_MAX_ATTEMPTS=3
DRY_RUN=false
DEMO_ONLY=true
ALLOW_AUTO_CLICK=true
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

Gerar integridade:

```powershell
python main.py --write-integrity
```

Verificar integridade:

```powershell
python main.py --check-integrity
```

Exportar auditoria:

```powershell
python main.py --export-audit
```

Rodar o app:

```powershell
python main.py
```

## UI Premium Desktop

Rodar:

```powershell
cd "C:\Users\junin\OneDrive\Documentos\New project\iqoption-assistant"
.venv\Scripts\activate
pip install -r requirements.txt
python -m ui.app
```

Fluxo:

- o app desktop sempre inicia em `PARADO`
- `START` abre modal de PIN e so arma `DEMO_ARMADO` se PIN, integridade, conta DEMO e guardas passarem
- `STOP` interrompe tudo imediatamente e cria a `STOP_TRADING.flag`
- os logs atualizam em tempo real sem travar a UI
- o painel mostra dashboard, sinais, seguranca, logs e configuracoes em modo SaaS local
- use `Atualizar Conta` depois de trocar manualmente para DEMO na traderoom, caso a UI ainda mostre `DESCONHECIDO`
- a aba `Inteligencia` usa o modulo compartilhado `market_intelligence` em modo local ou online

## Inteligencia de Mercado Compartilhada

O projeto agora usa um modulo compartilhado em `market_intelligence/` para gerar:

- `COMPRA`
- `VENDA`
- `NAO_OPERAR`

Sempre com:

- score
- motivos
- bloqueios
- validade curta
- fontes de dados

Fontes publicas e oficiais integradas nesta primeira camada:

- OANDA v20 para Forex
- Binance para candles publicos de cripto
- BLS para macro dos EUA
- FRED para series macro
- calendarios publicos do Fed/ECB

Variaveis de ambiente:

```env
MARKET_MODE=local
MARKET_API_URL=
MARKET_API_TOKEN=
OANDA_API_TOKEN=
OANDA_ACCOUNT_ID=
FRED_API_KEY=
BLS_API_KEY=
MIN_CONFIDENCE_SCORE=70
BLOCK_NEWS_MINUTES_BEFORE=30
BLOCK_NEWS_MINUTES_AFTER=15
```

Modos:

- `MARKET_MODE=local`: o app desktop roda a analise dentro do proprio Windows
- `MARKET_MODE=online`: o app chama a API hospedada na VPS/Fab Web

Fluxo recomendado:

1. Abra a IQ Option
2. Confirme conta `DEMO`
3. Use `Atualizar Conta`
4. Abra a aba `Inteligencia`
5. Clique `Atualizar Analise`
6. Se a decisao for boa, use `Enviar para Sinais`

## Empacotamento Windows

Gerar o executavel `.exe`:

```powershell
cd "C:\Users\junin\OneDrive\Documentos\New project\iqoption-assistant"
.venv\Scripts\activate
pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

Saida esperada:

```text
dist/
  iqoption-assistant/
    iqoption-assistant.exe
    IQ Option Assistant.lnk
    .env
    .env.example
    README.md
    storage/
      integrity_manifest.json
      logs/
```

O build do Windows ja gera o manifesto automaticamente em:

```text
dist\iqoption-assistant\storage\integrity_manifest.json
```

Esse manifesto agora nasce no perfil correto do pacote Windows (`dist`), nao mais no perfil do codigo-fonte.

Rodar o executavel:

```powershell
cd ".\dist\iqoption-assistant"
.\iqoption-assistant.exe
```

Editar `.env`:

- abra `dist\iqoption-assistant\.env`
- ajuste apenas os valores necessarios
- mantenha `DEMO_ONLY=true` para nunca liberar conta real

Resetar a `STOP` flag:

```powershell
Remove-Item ".\dist\iqoption-assistant\storage\STOP_TRADING.flag" -ErrorAction SilentlyContinue
```

Fallback manual para regenerar manifesto:

```powershell
cd "C:\Users\junin\OneDrive\Documentos\New project\iqoption-assistant"
$env:IQASSISTANT_BASE_DIR="C:\Users\junin\OneDrive\Documentos\New project\iqoption-assistant\dist\iqoption-assistant"
.\.venv\Scripts\python.exe main.py --write-integrity
Remove-Item Env:IQASSISTANT_BASE_DIR
```

No app, se precisar, voce ainda pode usar:

- `Configuracoes` -> `Gerar Manifesto`
- `Dashboard` -> `Verificar Integridade`
- `Dashboard` -> `Atualizar Conta`
- `Inteligencia` -> `Atualizar Analise`

Ver logs:

- log operacional: `dist\iqoption-assistant\storage\logs\trading-assistant.log`
- auditoria exportada: `dist\iqoption-assistant\storage\logs\audit.exported.log`
- o executavel continua lendo `.env`, `storage` e `README.md` externamente, sem embutir esses arquivos como segredo interno

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
- `PARADO`: estado inicial obrigatorio em toda nova execucao.

## Fluxo esperado

1. Verifica se o Chrome esta aberto.
2. Se houver Chrome controlavel com porta de depuracao, conecta.
3. Se nao houver, abre uma instancia controlada do Chrome.
4. Acessa `https://iqoption.com/traderoom`.
5. Se houver login pendente, pausa para login manual.
6. Tenta preparar a selecao do ativo informado.
7. Detecta visualmente o modo da conta:
   - `DEMO`
   - `REAL`
   - `DESCONHECIDO`
8. Se a conta continuar `DESCONHECIDO`, selecione manualmente a conta demo na IQ Option e clique em `Atualizar Conta`.
9. Mostra a UI desktop premium com `START` e `STOP`.
10. `START` pede o PIN `12345690`, valida integridade e so arma a sessao em demo.
11. Registra hotkeys:
   - `CTRL + SHIFT + A` para `START`
   - `CTRL + SHIFT + S` para `STOP`
12. Mostra confirmacao:
   - `Confirmar entrada? ativo=X direcao=Y horario=Z expiracao=W`
13. Dispara alerta 10 segundos antes.
14. No horario exato:
   - em `dry-run`: apenas destaca o botao e orienta clique manual
   - em demo armado: so clica se todos os guardas passarem

## Deteccao de conta DEMO

O app agora registra logs mais detalhados para ajudar a diagnosticar a conta atual, incluindo:

- URL atual
- titulo da pagina
- estado de login detectado
- textos visiveis relacionados a `Demo`, `Practice`, `Real` e `Balance`

Se a traderoom abrir mas a UI continuar mostrando `DESCONHECIDO`:

1. troque manualmente para a conta demo na IQ Option
2. volte ao app
3. clique em `Atualizar Conta`

Se o app detectar `REAL`, o `START` continuara bloqueado e a UI mostrara alerta explicito.

## API Online de Inteligencia

Quando `MARKET_MODE=online`, o app Windows pode consumir:

- `POST /api/v1/market/analyze`
- `GET /api/v1/market/status`
- `GET /api/v1/market/latest?asset=EUR/USD`

O token deve ficar no `.env`:

```env
MARKET_API_TOKEN=change-me
```

## Armando a sessao DEMO

Somente depois do `START` a sessao fica armada para auto-click em demo. Depois disso, o app nao pede confirmacao manual a cada entrada. A sessao desarma automaticamente se:

- o usuario clicar em `STOP`
- o usuario fechar a janela flutuante
- a hotkey `CTRL + SHIFT + S` for pressionada
- atingir o limite de operacoes
- houver erro
- o navegador fechar
- o ativo mudar inesperadamente
- o horario do sinal expirar

Conta real continua bloqueada mesmo apos o `START`.

## Logs

Os logs sao gravados em:

```text
storage/logs/trading-assistant.log
```

Auditoria local cifrada:

```text
storage/logs/audit.secure.log
```

Exportacao legivel da auditoria:

```text
storage/logs/audit.exported.log
```

Observacao:
- se `ENABLE_LOCAL_ENCRYPTION=true` e `ASSISTANT_MASTER_KEY` estiver definido, a trilha de auditoria sera gravada cifrada
- isso protege os artefatos locais em repouso
- isso nao foi feito para mascarar automacao da plataforma

## Testes

```powershell
pytest
```

## Limitacoes conhecidas

- A IQ Option pode mudar seletores e textos da interface.
- A automacao tenta localizar campos de busca e botoes conhecidos, mas pode precisar de ajuste fino visual.
- O projeto nao promete lucro, nao calcula martingale e nao substitui decisao humana.
- `MAX_DAILY_LOSS` fica reservado para integracao futura com leitura de resultado; nesta fase ele nao recalcula perdas automaticamente.
