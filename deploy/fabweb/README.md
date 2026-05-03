# Fabweb Fallback Publish

Arquivos esperados no subdominio `roboiqopition.juninnzxtec.com.br`:

- `api.php`
- `.htaccess`
- `index.html`
- `assets/`

Configuracao opcional da API publica:

- copie `.env.api.example` para `.env.api`
- ajuste:
  - `API_PUBLIC=true`
  - `API_TOKEN=`

Comportamento:

- se `API_TOKEN` estiver vazio, a API fica publica
- se `API_TOKEN` estiver preenchido, enviar `Authorization: Bearer TOKEN`

Endpoints expostos:

- `GET /api/v1/health/detailed`
- `GET /api/v1/market/status`
- `GET /api/v1/market/latest?asset=EUR/USD&timeframe=M1`
- `POST /api/v1/market/analyze`

Teste rapido local:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_public_api.ps1
```

Logs no host:

- `storage/logs/api_access.log`
