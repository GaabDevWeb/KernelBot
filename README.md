# KernelBot

Runtime HTTP do tutor académico: RAG BM25, contexto, memória de grupo, provider LLM e painel operacional.

OrbitBot (WhatsApp) é repositório separado — ver secção [WhatsApp / Orbit](#whatsapp--orbit).

## Requisitos

- Python 3.11+
- MySQL com tabela `knowledge` indexada
- Node 18+ (apenas para Orbit)
- Chave LLM: OpenRouter ou Cursor (`ACL_LLM_PROVIDER`)

## Configuração

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencher DB_*, tokens, provider
```

Variáveis mínimas: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, provider LLM, e em produção `ACL_API_BEARER_TOKEN` + `ACL_INTERNAL_BEARER_TOKEN`.

Ver `.env.example` e `docs/operations/v1-production-runbook.md`.

### Indexar conhecimento (primeira vez)

```bash
./bin/ingest-jsons.sh          # jsons/ → MySQL
# ou staging completo:
./bin/staging-setup.sh
```

## Inicialização

```bash
PYTHONPATH=. .venv/bin/python main.py
# → http://127.0.0.1:8001
```

Docker:

```bash
cp .env.docker.example .env
docker compose up -d --build
```

## Health

```bash
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/v1/health
```

Painel ops: `/ops/` · Traces: `/traces/` (requer `ACL_INTERNAL_BEARER_TOKEN`).

## Ollama / LLM

Provider configurável via `ACL_LLM_PROVIDER` (`openrouter` | `cursor`). Modelos em `ACL_MODELS`. Timeout e retry em `kernel/providers/chat_provider.py`.

Não versionar modelos, weights ou caches Ollama.

## WhatsApp / Orbit

```bash
cd ../OrbitBot
npm ci
cp .env.example .env   # KERNEL_API_URL=http://127.0.0.1:8001
npm start
```

Orbit envia `POST /v1/chat` ao Kernel. Sessão Baileys fica em `OrbitBot/auth/` (gitignored).

## Estrutura mínima

```
main.py          → entrypoint
app/ api/        → FastAPI
kernel/          → RAG, contexto, memória, provider
adapters/        → outbound comms
templates/       → ops + traces UI
context/         → calendário + contexto institucional
jsons/           → fonte ingestão RAG
bin/             → ingest e staging
data/            → SQLite runtime (local, gitignored)
```

Detalhe: `docs/runtime-manifest.md`.

## Troubleshooting

| Problema | Acção |
|----------|-------|
| Boot falha “system_prompt.txt” | Verificar `kernel/policies/systemPrompt/` |
| RAG vazio | Correr ingest; confirmar MySQL `knowledge` |
| 401 no chat | `ACL_API_BEARER_TOKEN` / header Authorization |
| Orbit não responde | Kernel up? `KERNEL_API_URL` correcto? |
| Catálogo 503 | `ACL_CATALOG_ENABLED=true` + `ACL_CATALOG_JSON_DIR` |

API: `docs/API_SPEC.md` · Produção: `docs/operations/v1-production-runbook.md`.
