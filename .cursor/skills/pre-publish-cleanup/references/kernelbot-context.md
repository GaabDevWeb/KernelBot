# Contexto KernelBot

Carregar na **Fase 0** ao executar esta skill neste repositório.

## Entrypoints e camadas

```
main.py → app/factory.py → api/routes.py
                         → frontend/ (static /src, /assets)
                         → engine/
templates/index.html
```

## Documentação principal

- `README.md` — setup, deploy, testes, arquitectura
- `documentation.md` — complementar; verificar overlap com README antes de manter ambos

## Scripts operacionais (manter)

| Script | Uso |
|--------|-----|
| `bin/staging-setup.sh`, `bin/staging-serve.sh` | staging local |
| `bin/validate-frontend.py` | smoke Playwright (README) |
| `bin/validate-frontend.mjs` | alternativa Node |
| `bin/ingest-*.sh` | ingestão conteúdo |

## Deploy

- `Dockerfile`, `docker-compose*.yml`, `railway.toml`
- `.env.example`, `.env.docker.example`, `.env.railway.example`

## `.gitignore` relevante

Já ignorados (não versionar; podem existir localmente):

- `.env`, `.env.*` (excepto `*.example`)
- `node_modules/`, `.venv/`, `venv/`, `__pycache__/`
- `.agent_history.md`, `results/`, `scripts/` (pasta raiz)
- `docs/PROMPT-AGENTE-*.md`
- `tests/` — **atenção:** pasta ignorada no git; testes existem localmente para pytest

## Candidatos frequentes a remoção (verificar sempre)

Raiz:

- `audit-*.png` — screenshots de sessões QA
- `QA_PRE_LANCAMENTO_AUDIT.md`, `ROADMAP_QA_V2_IMPLEMENTATION.md`
- `PERGUNTAS-SMOKE-*.md`, `TESTE-LOCAL.md`, `z-respostas.md`
- `.playwright-mcp/` — logs e snapshots MCP

`docs/`:

- `lighthouse-baseline-v2.md`, `qa-v2-post-roadmap.md` — relatórios pós-implementação
- `PROMPT-AGENTE-*.md` — prompts one-shot (gitignored)
- `RELATORIO-INTEGRACAO-DISCIPLINAS.md` — histórico se integração concluída

## README — limpeza pós-docs

Secção "Status" no README referencia ficheiros QA/roadmap. Após remoção, actualizar para reflectir estado "pronto para publicação" sem links mortos.

## Frontend

- ES modules em `frontend/src/`
- CSS em `frontend/assets/css/`
- Vendor em `frontend/src/vendor/` (marked, highlight) — verificar imports em `markdown.js` antes de remover

## Testes

```bash
PYTHONPATH=. pytest tests/ -q
python3 bin/validate-frontend.py
```

Playwright: `playwright install chromium` se necessário.
