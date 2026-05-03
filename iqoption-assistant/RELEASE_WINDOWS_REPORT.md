# RELEASE_WINDOWS_REPORT

## Resumo

Revisao final de release do app Windows `iqoption-assistant` empacotado em `dist/iqoption-assistant`.

Objetivo desta revisao:

- validar abertura do `.exe`
- validar fluxo de `START` com PIN
- validar `STOP` criando `STOP_TRADING.flag`
- validar logs
- validar exportacao de auditoria
- validar integridade depois do build
- validar `README.md` dentro do pacote `dist`
- manter todos os bloqueios de conta real

## Resultado Final

- Release do Windows: **APROVADA COM RESSALVAS CONTROLADAS**
- Bloqueios de conta real: **mantidos**
- Bypass/camuflagem: **nao adicionados**

## Checklist

| Item | Resultado | Evidencia |
|---|---|---|
| Abertura do `.exe` | OK | `dist/iqoption-assistant/iqoption-assistant.exe --smoke-test` executou sem erro |
| `START` pede PIN | OK | validado por automacao local em `MainWindow._request_start()` com `QInputDialog.getText` |
| `STOP` cria `STOP_TRADING.flag` | OK | validado chamando `AutoTrader.request_stop()` |
| Logs acessiveis | OK | `dist/iqoption-assistant/storage/logs/trading-assistant.log` criado |
| Exportacao de auditoria | OK | `python main.py --export-audit` retornou sucesso |
| Integridade depois do build | OK | manifesto presente em `dist/iqoption-assistant/storage/integrity_manifest.json` e validado no source |
| `README.md` do pacote `dist` | OK | `dist/iqoption-assistant/README.md` presente |
| `.env` externo editavel | OK | `dist/iqoption-assistant/.env` presente |
| `storage/` externo acessivel | OK | `dist/iqoption-assistant/storage/` presente |
| Atalho do app | OK | `dist/iqoption-assistant/IQ Option Assistant.lnk` presente |

## Comandos Usados

```powershell
cd "C:\Users\junin\OneDrive\Documentos\New project\iqoption-assistant"
.venv\Scripts\python.exe -m pytest
python -m compileall .
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
Test-Path ".\dist\iqoption-assistant\storage\integrity_manifest.json"
```

Validacao do executavel:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\dist\iqoption-assistant\iqoption-assistant.exe --smoke-test
```

Validacao de `START` pedindo PIN:

```powershell
.venv\Scripts\python.exe - <<'PY'
from pathlib import Path
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from ui.main_window import MainWindow
from ui import main_window as mw

app = QApplication([])
class FakeController(QObject):
    status_changed = Signal(dict)
    signals_changed = Signal(list)
    toast = Signal(str, str)
    action_finished = Signal(str, bool)
    request_start = Signal(str)
    request_stop = Signal()
    request_verify_integrity = Signal()
    request_export_audit = Signal()
    request_open_iq_option = Signal()
    request_clear_stop = Signal()
    request_add_signal = Signal(str, str, str, str)
    request_open_logs_folder = Signal()
    request_open_readme = Signal()
    def stop(self): pass

controller = FakeController()
captured = []
controller.request_start.connect(lambda pin: captured.append(pin))
window = MainWindow(controller, Path.cwd())
orig = mw.QInputDialog.getText
mw.QInputDialog.getText = staticmethod(lambda *args, **kwargs: ('12345690', True))
window._request_start()
mw.QInputDialog.getText = orig
assert captured == ['12345690']
print('START_PIN_MODAL_OK')
PY
```

Validacao de `STOP`:

```powershell
.venv\Scripts\python.exe - <<'PY'
from pathlib import Path
import logging
from auto_trader import AutoTrader
from config import load_settings
from integrity_guard import IntegrityGuard
from pin_guard import PinGuard
from security import SecurityManager

class DummyController:
    pass

settings = load_settings(Path.cwd())
if settings.stop_file.exists():
    settings.stop_file.unlink()
logger = logging.getLogger("release_stop_test")
logger.handlers.clear()
logger.addHandler(logging.StreamHandler())
logger.setLevel("INFO")
trader = AutoTrader(
    settings,
    DummyController(),
    logger,
    SecurityManager(settings),
    PinGuard(settings, logger),
    IntegrityGuard(settings),
)
trader.request_stop("release stop validation")
assert settings.stop_file.exists()
settings.stop_file.unlink(missing_ok=True)
print("STOP_FLAG_OK")
PY
```

Validacao de auditoria e integridade:

```powershell
.venv\Scripts\python.exe main.py --write-integrity
.venv\Scripts\python.exe main.py --check-integrity
.venv\Scripts\python.exe main.py --export-audit
```

## Resultados Observados

### 1. Executavel

- `dist/iqoption-assistant/iqoption-assistant.exe` gerado com sucesso
- smoke test do `.exe` executado sem erro

### 2. Arquivos externos

Presentes no pacote:

- `dist/iqoption-assistant/.env`
- `dist/iqoption-assistant/.env.example`
- `dist/iqoption-assistant/README.md`
- `dist/iqoption-assistant/storage/`
- `dist/iqoption-assistant/storage/integrity_manifest.json`
- `dist/iqoption-assistant/storage/logs/`
- `dist/iqoption-assistant/IQ Option Assistant.lnk`

### 3. Logs

- `dist/iqoption-assistant/storage/logs/trading-assistant.log` foi criado no teste do executavel

### 4. Auditoria

- `python main.py --export-audit` executou com sucesso
- arquivo exportado: `storage/logs/audit.exported.log`

### 5. Integridade

- manifesto regravado com `python main.py --write-integrity`
- checagem passou com `python main.py --check-integrity`
- manifesto copiado para `dist/iqoption-assistant/storage/integrity_manifest.json`
- checagem de existencia:

```powershell
Test-Path ".\dist\iqoption-assistant\storage\integrity_manifest.json"
```

Resultado observado:

```text
True
```

## Ressalvas Controladas

1. O pacote `dist` atual foi empacotado a partir da UI (`python -m ui.app`), entao o `.exe` nao expõe diretamente comandos CLI como `--check-integrity` ou `--export-audit`.
2. A validacao de `START` pedindo PIN foi feita por automacao do fluxo de UI no codigo, nao por clique manual humano no `.exe`.
3. A validacao de `STOP` criando a flag foi feita no fluxo real do `AutoTrader`, mas fora de uma sessao de traderoom conectada.

Essas ressalvas nao removem protecoes nem abrem caminho para conta real; apenas delimitam o que foi automatizado na revisao.

## Proximos Cuidados

1. Antes de uso real em DEMO, revisar o `.env` em `dist/iqoption-assistant/.env`.
2. Manter `DEMO_ONLY=true`.
3. Nao usar `ALLOW_AUTO_CLICK=true` em ambiente nao validado manualmente.
4. Se o app travar em `PARADO`, verificar:
   - `storage/STOP_TRADING.flag`
   - `storage/logs/trading-assistant.log`
   - `storage/logs/audit.exported.log`
5. Se o layout da IQ Option mudar, revisar seletores em `browser_controller.py`.
6. Se for necessario validar integridade no pacote final, a proxima melhoria correta e adicionar um comando de manutencao no `.exe` ou um utilitario companion para release.
