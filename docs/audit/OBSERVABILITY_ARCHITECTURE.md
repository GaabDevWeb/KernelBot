# OBSERVABILITY_ARCHITECTURE

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `kernel-observability-implementation` |

## Objectivo

Observar o Kernel **sem** alterar a semântica pública de respostas (excepto campos aditivos: `X-Request-Id`, `metadata.request_id`).

## Camadas

```text
HTTP /internal/*  ──Bearer──►  api/internal_routes.py
                                    │
                                    ▼
                          kernel/inspect/sdk.py
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
             PipelineRecorder   Settings/RAG    PinnedStore
             (ring buffer)      SearchEngine    Disciplines
```

SDK (sem HTTP):

```python
from kernel.inspect import (
    inspect_pipeline as pipeline,
    inspect_rag as rag,
    inspect_context as context,
    inspect_metrics as metrics,
)
# ou: kernel.inspect.sdk.pipeline(request_id)
```

Funções em `kernel/inspect/sdk.py`: `pipeline`, `rag`, `rag_query`, `context`, `prompt`, `disciplines`, `models`, `metrics`, `system`, `memory_session`, `health_deep`.

## Fluxo de captura

```text
RequestIdMiddleware → request.state.request_id
        ↓
POST /chat | /search
        ↓
PipelineRecorder.put(PipelineRecord)
  - rag: candidates found/selected/discarded + RetrievalTrace
  - context: ContextTrace summary + tamanhos
  - prompt: messages[] se ACL_INTERNAL_STORE_PROMPTS=true
  - provider/response: meta pós-agregação (chat JSON)
        ↓
GET /internal/pipeline/{request_id}
```

## Endpoints internos (Bearer)

| Método | Path |
|--------|------|
| GET | `/internal/system` |
| GET | `/internal/disciplines` |
| GET | `/internal/rag` |
| GET | `/internal/rag/query/{request_id}` |
| GET | `/internal/context/{request_id}` |
| GET | `/internal/prompt/{request_id}` |
| GET | `/internal/pipeline/{request_id}` |
| GET | `/internal/models` |
| GET | `/internal/metrics` |
| GET | `/internal/health/deep` |
| GET | `/internal/memory/session/{session_id}` |
| GET | `/internal/requests/recent` |

Auth: `ACL_INTERNAL_BEARER_TOKEN` ou fallback `ACL_RELOAD_BEARER_TOKEN`.

## O que **não** faz

- Não muda ranking BM25, grounding, nem providers.
- Não introduz filas/microserviços.
- Não persiste prompts em disco (só RAM, TTL por capacidade do ring buffer).
- Não expõe memória por `user_id` (inexistente) — só `session_id`.

## Limitações conscientes

- Recorder process-local (como pin/rate-limit).
- `tokens_used` continua a ser fragmentos (documentado nos payloads).
- Stream SSE: provider meta parcial até haver agregação futura do stream.
