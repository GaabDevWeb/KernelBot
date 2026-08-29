# Runtime manifest — KernelBot (true-kernel)

Branch operacional mínima. OrbitBot vive em repositório irmão (`../OrbitBot`).

## Entrypoints

| Componente | Comando |
|------------|---------|
| Kernel HTTP | `PYTHONPATH=. .venv/bin/python main.py` ou `uvicorn main:app --host 127.0.0.1 --port 8001` |
| Orbit WhatsApp | `cd ../OrbitBot && npm start` (ver README Orbit) |
| Ingest RAG | `./bin/ingest-jsons.sh` → MySQL `knowledge` |
| Staging local | `./bin/staging-setup.sh` + `./bin/staging-serve.sh` |

## Diretórios essenciais

| Path | Papel |
|------|-------|
| `kernel/` | Domínio: RAG, contexto, memória, provider, traces |
| `api/` + `app/` | FastAPI, routers, lifespan |
| `adapters/` | Outbound WhatsApp/Discord (comms) |
| `templates/` | Ops Center + painel de traces |
| `context/` | Contexto institucional + `calendar.json` |
| `kernel/policies/systemPrompt/` | Prompts de runtime (obrigatórios no boot) |
| `kernel/disciplines/disciplines.json` | Metadados de disciplinas |
| `kernel/context/domain_experts.json` | Domain router (se `ACL_DOMAIN_ROUTER=true`) |
| `jsons/` | Fonte de ingestão → MySQL (não lida directamente no chat) |
| `docker/` | `init-knowledge.sql` (schema MySQL) |
| `bin/` | Scripts operacionais (ingest, staging) |
| `data/` | SQLite runtime (gitignored) |

## Configuração

- `.env.example` — contrato de variáveis
- Boot fail-fast em `production`: tokens, workers, auth
- MySQL `DB_*` — índice BM25 (`knowledge`)
- LLM: `ACL_LLM_PROVIDER` + chaves (`OPENROUTER_*` ou `CURSOR_*`)

## Dados runtime vs ingestão

| Artefacto | Runtime chat | Ingest |
|-----------|--------------|--------|
| MySQL `knowledge` | **Sim** | `jsons_ingest`, wiki ingest |
| `jsons/**/*.json` | Não | Sim |
| `jsons/index.json` | Não | Índice humano |
| SQLite `data/*.sqlite3` | Sim | criado no boot |
| ISS `lessons.json` | Se `ACL_CATALOG_ENABLED=true` | externo |

## Integração Orbit

- Orbit → Kernel: `POST /v1/chat`, header `X-Message-Id`
- Kernel → Orbit: `ORBIT_INTERNAL_URL` (comms outbound)
- Tokens: `ACL_API_BEARER_TOKEN` (canal) + `ACL_INTERNAL_BEARER_TOKEN` (ops/traces)

## Deliberadamente fora desta branch

- `tests/`, fixtures, golden sets
- `memory/*` evidências de benchmark
- Documentação histórica (ADRs, PRDs, wiki dev)
- `.cursor/`, agent prompts, notebooks
- `optimization/` (relatórios de dev)
- CI de desenvolvimento

## Health

- `GET /health` — liveness Kernel
- `GET /v1/health` — alias
- Ops: `/ops/*`, Traces: `/traces/*` (auth interno)
