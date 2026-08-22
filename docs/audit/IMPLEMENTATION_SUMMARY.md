# IMPLEMENTATION_SUMMARY

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `kernel-observability-implementation` |
| Testes | `pytest tests/ -q` → **10 passed** |

## O que foi feito

1. **Revisão independente** da auditoria → `AUDIT_REVIEW.md`
2. **Plano de evolução** → `KERNEL_EVOLUTION_PLAN.md`
3. **Fix P0** `_search_kernel` → `_search_engine.search_candidates` (restaura `/chat`)
4. **Observabilidade**
   - `RequestIdMiddleware` (`X-Request-Id`)
   - `kernel/inspect/` (recorder + SDK)
   - `api/internal_routes.py` (`/internal/*`)
   - captura em `/chat` e `/search`
5. **Docs** → `OBSERVABILITY_ARCHITECTURE.md` + este sumário
6. **Testes** → `tests/test_internal_api.py`

## O que NÃO foi alterado (de propósito)

- Algoritmo BM25 / thresholds / grounding
- Fail-open de disciplina
- Semântica de pin
- Lista de modelos / temperature
- Contrato público JSON/SSE (só aditivos: request_id)

## Como usar

```bash
# token: ACL_INTERNAL_BEARER_TOKEN ou ACL_RELOAD_BEARER_TOKEN no .env
export TOKEN=...

curl -sS http://127.0.0.1:8001/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"O que é BM25?","channel":"cli"}' | jq '.metadata.request_id'

RID=... # do passo anterior
curl -sS -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8001/internal/pipeline/$RID | jq .

# SDK
python - <<'PY'
from kernel.inspect.sdk import pipeline, metrics
print(pipeline("..."))
PY
```

## Ficheiros tocados (implementação)

| Path | Papel |
|------|-------|
| `kernel/orchestrator/context.py` | Fix P0 + campos observabilidade no result |
| `kernel/inspect/*` | Recorder + SDK |
| `api/internal_routes.py` | HTTP interno |
| `api/routes.py` | Wiring recorder |
| `app/factory.py` | Middleware request_id + router interno |
| `tests/test_internal_api.py` | Aceite observabilidade |
| `docs/audit/*` | Entrega documental |

## Próximos passos recomendados

1. Reiniciar servidor na branch de implementação
2. Configurar `ACL_INTERNAL_BEARER_TOKEN` (ou reusar reload token)
3. (Opcional) CR-3 fail-closed disciplina — mudança de comportamento, RF separado
4. (Opcional) tokens reais do provider
