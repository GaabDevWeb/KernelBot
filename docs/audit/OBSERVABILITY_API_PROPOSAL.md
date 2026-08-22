# OBSERVABILITY_API_PROPOSAL — API Interna de Observabilidade

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Base | Auditoria SA1–SA10 + código actual |
| Estado | **Proposta** — não implementar nesta branch de auditoria |
| Princípio | Cada endpoint justifica-se por sinal **já existente** ou por lacuna **explicitamente medida** |

## 1. Objectivo

Expor, para operadores e engenharia, **o que o Kernel fez** num pedido — sem servir UI de produto e sem alterar a semântica pública de `/chat` e `/search`.

Público-alvo: internos (Bearer ops / rede privada). **Não** é contrato de adapters de canal.

## 2. Inventário: o que já existe vs o que falta

### Já existe (reutilizável)

| Sinal | Onde nasce hoje |
|-------|-----------------|
| Decisão RAG `reason`, `confidence`, scores, coverage | `RetrievalTrace` / `build_decision` |
| Fontes / source_details / label | `ContextTrace` |
| Pin state | `PinnedSessionStore` + campos no trace |
| Grounding policy / mode | Settings + meta |
| `ACL_META` v3 | `ChatProvider._build_meta` |
| Logs estruturados por módulo | `structured_log.log_event` (`search`, `context`, `decision`, `provider`, `database`) |
| Drift catálogo | `GET /health/catalog` + `catalog_drift_report` |
| Lista disciplinas SSOT | `disciplines.json` + helpers |
| Modelos / provider config | `Settings` |
| Duração stream LLM (`elapsed_ms`) | logs provider |
| Rebuild BM25 timing | logs search |

### Não existe (lacunas medidas)

| Lacuna | Impacto |
|--------|---------|
| `request_id` / correlação HTTP↔logs | Impossível juntar eventos de um turno |
| Store de pipeline/prompt por request | Sem replay/inspeção pós-facto |
| Timings por etapa (parse, BM25, assemble, TTFT) | Só parcial (stream/rebuild) |
| Tokens reais / custo | `tokens_used` = contagem de **fragmentos SSE**, não tokens do provider |
| Memória por `user_id` | Só pin por `session_id` em RAM |
| Métricas Prometheus / OTel | Inexistente |
| Readiness (MySQL/índice/provider) | `/health` é liveness estática |

## 3. Pré-requisitos de implementação (fora desta auditoria)

Ordem sugerida **antes** de expor a API interna:

1. **Corrigir** referência `_search_kernel` → `_search_engine` (bloqueia captura real de pipeline `/chat`).
2. Introduzir `request_id` (UUID) no middleware; propagar a logs e resposta (`X-Request-Id`).
3. `PipelineRecorder` in-process (ring buffer) alimentado por ContextManager + ChatProvider — **sem** mudar resposta pública excepto headers/meta opcional.
4. Auth: reutilizar `ACL_RELOAD_BEARER_TOKEN` ou token dedicado `ACL_INTERNAL_BEARER_TOKEN`.

## 4. Endpoints propostos (justificados)

Prefixo sugerido: `/internal` · Auth: Bearer ops · Content-Type: JSON.

### 4.1 Inventário estático (sem request_id)

#### `GET /internal/system-map`

**Justificativa:** espelha SYSTEM_MAP + estado runtime (versões, paths de prompts, provider activo).  
**Fonte:** `Settings`, paths `policies/systemPrompt`, contagens `SearchEngine`.

#### `GET /internal/disciplines`

**Justificativa:** SSOT de comandos/labels já em `disciplines.json` + silos reais no índice.  
**Payload sugerido:**
```json
{
  "registry": [{"id","label","command","query_markers"}],
  "indexed_silos": ["python", "doc", "..."],
  "catalog_enabled": true
}
```

#### `GET /internal/models`

**Justificativa:** provider/modelos já em Settings + lista hardcoded OpenRouter no provider.  
**Payload:** `llm_provider`, `cursor_model`, `openrouter_models[]`, `temperature_fixed` (0.7 se openrouter).

#### `GET /internal/rag/config`

**Justificativa:** thresholds ACL_* já em Settings — hoje só via `.env`.  
**Payload:** `candidate_k`, `top_k`, `min_score`, margins, coverages, chunking constants, grounding_policy.

#### `GET /internal/metrics` (snapshot in-process)

**Justificativa:** agregar contadores já logáveis (sem Prometheus na v1).  
**Payload mínimo:**
```json
{
  "requests_total": 0,
  "chat_errors": 0,
  "search_total": 0,
  "rate_limited": 0,
  "provider_fallbacks": 0,
  "index_chunks": 0,
  "index_silos": 0,
  "uptime_s": 0
}
```
*Nota:* exige instrumentação nova mínima (contadores); não inventar custo $ sem tokens reais.

---

### 4.2 Inspeção por pedido (requer PipelineRecorder)

#### `GET /internal/pipeline/{request_id}`

**Justificativa:** orquestra o que SA3 mapeou — único sítio para “pipeline completo”.  
**Payload (campos derivados do código actual):**
```json
{
  "request_id": "...",
  "channel": "cli",
  "user_id": null,
  "session_id": "...",
  "message_preview": "...",
  "stages": [
    {"name": "validate", "ok": true, "ms": null},
    {"name": "scope", "discipline_command": null, "discipline_filter": "..."},
    {"name": "catalog", "match": null},
    {"name": "retrieval", "reason": "ok", "confidence": "high"},
    {"name": "assemble", "grounding_policy": "anchored"},
    {"name": "provider", "llm_called": true, "model": "...", "elapsed_ms": 0},
    {"name": "post_generation", "flags": []}
  ],
  "error": null
}
```

#### `GET /internal/rag/query/{request_id}`

**Justificativa:** projecta `RetrievalTrace` + candidatos já calculados em `build_decision`.  
**Payload:** query normalizada, termos, `candidate_k` hits com scores, selected, margins, coverage, reason.

#### `GET /internal/context/{request_id}`

**Justificativa:** `ContextTrace` + resumo do system montado (tamanhos, não necessariamente texto completo).  
**Payload:** label, sources, pin_*, scope_hint, catalog_match, `system_chars`, `history_turns`, `chunk_count`.

#### `GET /internal/prompts/{request_id}`

**Justificativa:** mensagens exactas enviadas ao LLM (`BuildMessagesResult.messages`) — **alto risco PII**.  
**Controlos obrigatórios:** Bearer + flag `ACL_INTERNAL_PROMPT_STORE=true` + retenção curta (ex. 15 min) + redacção.  
**Payload:** lista `{role, content}` ou hash+tamanho se store desactivado.

#### `GET /internal/memory/{session_id}`

**Justificativa:** pin já vive em `PinnedSessionStore` — **não** há memória por `user_id`.  
**Nota de desenho:** o exemplo da missão `GET /internal/memory/{user_id}` **não** mapeia o código actual.  
**Proposta alinhada ao código:**
- `GET /internal/memory/session/{session_id}` → pin actual (chunks meta, turns left, scope_key)
- `GET /internal/memory/user/{user_id}` → **404/501** até existir persistência por utilizador (documentar como futuro)

---

### 4.3 Endpoints da missão — mapeamento

| Pedido na missão | Proposta | Justificativa |
|------------------|----------|---------------|
| `GET /internal/disciplines` | ✅ igual | `disciplines.json` + silos |
| `GET /internal/rag` | ✅ como `/internal/rag/config` + opcional status índice | Settings + SearchEngine stats |
| `GET /internal/rag/query/{id}` | ✅ | RetrievalTrace |
| `GET /internal/pipeline/{request_id}` | ✅ | orquestração SA3 |
| `GET /internal/context/{request_id}` | ✅ | ContextTrace |
| `GET /internal/prompts/{request_id}` | ✅ com gate PII | messages[] |
| `GET /internal/memory/{user_id}` | ⚠️ **adaptar** → session | pin só por session_id |
| `GET /internal/metrics` | ✅ snapshot | logs/contadores |
| `GET /internal/models` | ✅ | Settings/provider |
| `GET /internal/system-map` | ✅ | mapa estático+runtime |

### Endpoints adicionais justificados (não na lista original)

| Endpoint | Porquê |
|----------|--------|
| `GET /internal/health/ready` | `/health` actual não verifica MySQL/índice/provider |
| `GET /internal/catalog/drift` | Reusa lógica de `/health/catalog` sob namespace internal |
| `GET /internal/requests/recent` | Lista request_ids do ring buffer (debug ops) |

## 5. Modelo de dados do recorder (mínimo)

```text
PipelineRecord
  request_id: str
  created_at: datetime
  channel, user_id?, session_id?
  chat_request_summary
  retrieval: RetrievalTrace | null
  context: ContextTrace | null
  messages_ref: stored | hashed | none
  provider: {model, llm_called, elapsed_ms, tokens_used_fragments, error?}
  response_summary: {discipline, sources, confidence, decision}
  ttl_expires_at
```

Armazenamento v1: `dict` + `deque` in-process (alinhado a pin/rate_limit).  
v2 (fora de escopo): Redis/Postgres se multi-worker.

## 6. Segurança da API interna

- Bearer obrigatório (fail-closed se token ausente).
- Bind preferencial a localhost / rede privada (documentar; não forçar no Kernel público).
- Nunca expor `.env` secrets nos payloads.
- Prompts: opt-in + retenção + redacção (`structured_log.redact_secrets` como baseline).
- Rate limit próprio mais apertado que `/chat`.

## 7. Fora de escopo da proposta

- Alterar contrato público `/chat`/`/search` (excepto header `X-Request-Id` aditivo).
- Microserviços, Kafka, OpenTelemetry completo (pode ser fase 2).
- UI de observabilidade (consumidor = curl/CLI/Grafana futuro).
- Corrigir `_search_kernel` nesta auditoria (pré-requisito separado).

## 8. Critérios de aceite futuros (quando implementar)

1. Dado um `POST /chat` bem-sucedido, `GET /internal/pipeline/{id}` devolve stages coerentes com logs.
2. `GET /internal/rag/query/{id}` reflecte os mesmos `sources` que `ChatResponse`.
3. Sem Bearer → 401/503; com Bearer inválido → 401.
4. Suite pytest com recorder fake — sem MySQL/LLM reais.
5. Documentação actualiza `API_SPEC` com secção Internal (separada da API pública).

## 9. Ordem de entrega recomendada

```text
P0  Fix _search_kernel (desbloqueia observabilidade real do chat)
P1  request_id middleware + log HTTP final
P2  PipelineRecorder + GET /internal/pipeline|rag/query|context
P3  GET /internal/disciplines|models|rag/config|system-map|metrics
P4  Prompt store opt-in + memory/session
P5  readiness + métricas exportáveis
```

## Referências de auditoria

- [`SYSTEM_MAP.md`](SYSTEM_MAP.md)
- [`KERNEL_FLOW.md`](KERNEL_FLOW.md)
- [`API_MAP.md`](API_MAP.md)
- SA10 Observabilidade: [agent](5de58611-577b-47ba-80b0-a259e9695ab7)
