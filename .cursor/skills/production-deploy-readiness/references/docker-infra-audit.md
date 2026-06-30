# Auditoria Docker e infraestrutura

Carregar na **Fase 1**.

## Checklist Dockerfile

- [ ] Base image pinned (`python:3.12-slim-bookworm` ou documentar upgrade)
- [ ] `requirements-prod.txt` — sem deps de dev (pytest, playwright)
- [ ] `USER` non-root (`kernelbot`)
- [ ] `HEALTHCHECK` aponta para `/health` na `PORT` correcta
- [ ] `CMD` usa `0.0.0.0` e `${PORT:-8001}` (Railway/Fly compatível)
- [ ] `COPY` inclui todas as pastas runtime: `api`, `app`, `core`, `engine`, `frontend`, `templates`, `main.py`
- [ ] Não copia `.env`, `tests/`, `node_modules/`, `.venv/`

## Checklist `.dockerignore`

Comparar com `.gitignore`. Deve excluir:

- `.env`, `.env.*` (excepto se copiados intencionalmente — **não**)
- `node_modules/`, `.venv/`, `venv/`
- `tests/`, `__pycache__/`, `.pytest_cache/`
- Artefactos: `results/`, `.playwright-mcp/`, `audit-*.png`

## Docker Compose

Para cada `docker-compose*.yml`:

- [ ] Serviços, ports, volumes, env files documentados no README
- [ ] Sem credenciais hardcoded
- [ ] `docker compose config` válido (sem erros de sintaxe)
- [ ] Rede/volumes nomeados de forma consistente

## Ficheiros obsoletos

Se documentação referencia `Dockerfile.dev` ou `docker-compose.dev.yml` **inexistentes**:

1. Remover referência da doc, **ou**
2. Criar ficheiro só se realmente necessário (preferir não duplicar)

## Validação Docker

```bash
docker build -t kernelbot:audit .
docker compose -f docker-compose.yml config
docker run --rm -p 8001:8001 --env-file .env.example kernelbot:audit &
sleep 10
curl -fsS http://127.0.0.1:8001/health
```

Nota: build pode falhar sem `.env` real — usar env mínimo ou documentar pré-requisitos.

## Plataformas alvo (sanity check)

| Plataforma | Ficheiro / nota |
|------------|-----------------|
| Railway | `railway.toml`, `PORT` env |
| Docker/VPS | `Dockerfile`, `docker-compose.yml` |
| Coolify/Portainer | Compose + healthcheck |
| Render/Fly | `PORT`, health endpoint |

Não prometer compatibilidade sem validar `PORT`, healthcheck e variáveis injectadas.

## `.gitignore` produção

Confirmar que nunca versiona:

- `.env`, `.env.staging.local`
- Segredos, logs, coverage, artefactos MCP

Adicionar padrões em falta (`.playwright-mcp/`, `audit-*.png`).
