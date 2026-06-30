# Contexto KernelBot — Production Deploy

Carregar na **Fase 0**.

## Entrypoints

```
main.py → app/factory.py → api/routes.py
                         → frontend/ (/assets, /src)
                         → engine/
templates/index.html
```

## Ficheiros Docker / deploy (existentes no repo)

| Ficheiro | Uso |
|----------|-----|
| `Dockerfile` | Imagem produção Python 3.12-slim, `requirements-prod.txt`, healthcheck `/health` |
| `docker-compose.yml` | Compose produção local |
| `docker-compose.staging.yml` | MySQL staging :3307 |
| `docker-compose.deploy-staging.yml` | Deploy staging |
| `.dockerignore` | Exclusões de build |
| `railway.toml` | Deploy Railway |
| `.env.example` | Template principal |
| `.env.docker.example` | Variáveis Docker |
| `.env.railway.example` | Variáveis Railway |

**Não existem (verificar docs — corrigir referências obsoletas):**

- `Dockerfile.dev`
- `docker-compose.dev.yml`
- `.env.production` (usar `KERNELBOT_ENV=production` no `.env`)

## Produção — variáveis obrigatórias (README)

| Variável | Produção |
|----------|----------|
| `KERNELBOT_ENV=production` | Desactiva `no-store` forçado em `/src/` |
| `ACL_RELOAD_BEARER_TOKEN` | Protege `/health/catalog` e `/reload` |
| `ACL_CATALOG_ENABLED=true` | Catálogo ISS + `GET /api/curriculum` → 200 |
| `ACL_CATALOG_JSON_DIR` | Dir `lessons.json` / `search-index.json` |
| `DB_*` | MySQL com `knowledge` indexada |
| `KERNELBOT_FORCE_HSTS=true` | Recomendado atrás de proxy HTTPS |

Provider LLM: `ACL_LLM_PROVIDER` (`cursor` default ou `openrouter` + `OPENROUTER_API_KEY`).

## Segurança (código)

- `app/factory.py` — `SecurityHeadersMiddleware`, CSP em `/`, `/assets/`, `/src/`
- `api/routes.py` — rate limit `POST /chat` (30/IP/60s)
- Staging: `ACL_CATALOG_ENABLED=false` em `bin/staging-serve.sh` → `/api/curriculum` 503 **esperado**

## Dependências

| Ficheiro | Ambiente |
|----------|----------|
| `requirements-prod.txt` | Docker / produção |
| `requirements.txt` | Dev (+ pytest, playwright, etc.) |

## Scripts operacionais (`bin/`)

| Script | Manter |
|--------|--------|
| `staging-setup.sh`, `staging-serve.sh`, `staging-*.sh` | Staging local |
| `validate-frontend.py` | Smoke oficial (README) |
| `ingest-jsons.sh`, `ingest-wiki-doc.sh` | Ingestão conteúdo |

## Build frontend

- Tailwind CSS v4 — ver `package.json` scripts
- ES modules em `frontend/src/` — servidos estáticos em produção (sem bundler webpack)
- Vendor local: `frontend/src/vendor/` (marked, highlight)

## Health / rotas críticas

```bash
curl -sS http://127.0.0.1:8001/health
curl -sS http://127.0.0.1:8001/api/public-config
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/api/curriculum
```

## Documentação oficial

- `README.md` — setup, deploy, testes
- `documentation.md` — índice → `docs/wiki/`
- `docs/wiki/20-deploy-railway.md` — runbook Railway (se existir)

## CI/CD

Verificar `.github/workflows/` se existir; se ausente, documentar gap no relatório (não bloquear deploy manual Docker/Railway).

## Staging vs produção

| Aspeto | Staging | Produção |
|--------|---------|----------|
| `KERNELBOT_ENV` | `staging` | `production` |
| `ACL_CATALOG_ENABLED` | `false` (script) | `true` |
| Cache `/src/` | `no-store` | sem forçar dev cache |
