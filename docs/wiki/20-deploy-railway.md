# Deploy — Railway, Docker e VPS

[← Índice](README.md)

Runbook de produção. Variáveis detalhadas: [12-configuracao.md](12-configuracao.md). Staging local: [13-staging-testes.md](13-staging-testes.md).

## Pré-requisitos

| Item | Notas |
|------|-------|
| MySQL indexado | Tabela `knowledge` populada (pipeline ISS ou ingest manual) |
| LLM | OpenRouter recomendado em PaaS (`ACL_LLM_PROVIDER=openrouter`) |
| Catálogo ISS | `lessons.json` + `search-index.json` em `ACL_CATALOG_JSON_DIR` |
| Token reload | `ACL_RELOAD_BEARER_TOKEN` obrigatório em produção |

## Variáveis obrigatórias (produção)

```bash
KERNELBOT_ENV=production
ACL_LLM_PROVIDER=openrouter          # ou cursor (requer runtime adequado)
OPENROUTER_API_KEY=...               # se openrouter
ACL_RELOAD_BEARER_TOKEN=...          # protege /health/catalog e /reload
ACL_CATALOG_ENABLED=true
ACL_CATALOG_JSON_DIR=/caminho/ISS/content
DB_HOST=... DB_PORT=3306 DB_NAME=... DB_USER=... DB_PASSWORD=...
KERNELBOT_FORCE_HSTS=true            # recomendado atrás de HTTPS
```

Alias aceite: `KERNELBOT_RELOAD_TOKEN` (= `ACL_RELOAD_BEARER_TOKEN`).

**Não definir `PORT` manualmente no Railway** — a plataforma injecta; a app escuta `0.0.0.0:$PORT`.

Template: [`.env.railway.example`](../../.env.railway.example).

## Railway

1. Ligar repositório GitHub ao Railway.
2. Builder: `Dockerfile` (ver [`railway.toml`](../../railway.toml)).
3. Colar variáveis do `.env.railway.example` no dashboard.
4. Healthcheck: `/health` (timeout 180s no `railway.toml` — boot BM25 pode demorar).
5. Após deploy:

```bash
curl -sS https://SEU-DOMINIO/health
curl -sS https://SEU-DOMINIO/api/public-config
curl -sS -o /dev/null -w "%{http_code}\n" https://SEU-DOMINIO/api/curriculum
# → 200 com catálogo activo
```

6. Drift catálogo ↔ índice (operadores / CI ISS):

```bash
curl -sS -H "Authorization: Bearer SEU_TOKEN" https://SEU-DOMINIO/health/catalog
```

## Docker Compose (VPS / Coolify / Portainer)

```bash
cp .env.docker.example .env    # preencher MySQL + LLM + token
docker build -t kernelbot:latest .
docker compose up -d --build
```

- MySQL externo (Aiven): `DB_*` no `.env`.
- MySQL staging local: `docker compose -f docker-compose.staging.yml up -d` + `DB_HOST=host.docker.internal` `DB_PORT=3307`.
- Staging app+DB: `docker compose -f docker-compose.deploy-staging.yml up -d --build`.

Healthcheck: `GET /health` na porta publicada (`KERNELBOT_PUBLISH_PORT`, default 8001).

## Pós-deploy

| Verificação | Comando / acção |
|-------------|-----------------|
| Smoke UI | `python3 bin/validate-frontend.py` (contra URL pública ou túnel) |
| Reload índice | `POST /chat` com `message: "/reload"` + Bearer token |
| Rate limit | 30 req/min/IP em `POST /chat` — HTTP 429 acima |

## Rollback

1. Reverter deploy na plataforma (imagem/tag anterior).
2. Confirmar `GET /health` e `/api/public-config`.
3. Se drift de dados: re-correr ingest ISS Job 2 + `/reload`.

## Ficheiros de referência (repo)

| Ficheiro | Uso |
|----------|-----|
| `Dockerfile` | Imagem produção |
| `docker-compose.yml` | App containerizada |
| `requirements-prod.txt` | Deps Python (sem pytest/playwright) |
| `railway.toml` | Config Railway |
| `.dockerignore` | Exclusões de build |

**Nota:** este repo não inclui `Dockerfile.dev` nem `docker-compose.dev.yml` — staging usa `docker-compose.staging.yml` e scripts `bin/staging-*.sh`.

## Ver também

- [README — Deploy e produção](../../README.md#deploy-e-produção)
- [10-integracao-iss-fase5b.md](10-integracao-iss-fase5b.md)
- [14-seguranca-observabilidade.md](14-seguranca-observabilidade.md)
