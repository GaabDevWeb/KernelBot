# Group Memory — REPORT (feature/private-group-memory)

**Data:** 2026-08-27  
**Branch:** `feature/private-group-memory`  
**Merge:** não realizado (pedido explícito)

---

## 1. Auditoria (FASE 0)

| Componente | Estado pré-tarefa |
|------------|-------------------|
| `GroupMemoryStore` (SQLite + BM25 + recência) | Já implementado |
| Ingestão runtime via `/v1/groups/messages` | Já implementado |
| Integração ContextBuilder + tracing | Já implementado |
| Group Profile (opcional) | Já implementado |
| Painel `/ops/groups` | Já implementado |
| Parser WhatsApp `.txt` | **Ausente** |
| Context Router → GROUP_MEMORY | **Ausente** |
| `.gitignore` / `.dockerignore` dados privados | **Incompleto** |
| Retention configurável | **Ausente** |

---

## 2. Arquitetura implementada

```
WhatsApp export (.txt) ──► whatsapp_import.py (parse)
                              │
Orbit / v1 chat ─────────────► GroupMemoryStore (SQLite)
                              │ cache BM25 por (platform, channel_id)
                              ▼
                    search_historical(query limpa, BM25 × recência)
                              │
ContextRouter.use_group_memory ──► ContextBuilder ──► LLM
Knowledge RAG (separado, source_type=knowledge)
Recent transcript (separado)
```

---

## 3. Armazenamento

- **DB:** `data/group_memory.sqlite3` (config: `KERNEL_GROUP_MEMORY_DB_PATH`)
- **Tabela:** `group_messages` — UNIQUE `(platform, channel_id, message_id)`
- **Índice BM25:** in-memory por canal; invalidação incremental no insert (lazy rebuild)
- **Apagadas:** persistidas com metadata, **excluídas do BM25**

---

## 4. Privacidade

- `data/`, `*.sqlite3`, `**/messages.txt` → `.gitignore` + `.dockerignore`
- Placeholders: `data/.gitkeep`, `data/messages/.gitkeep`
- Testes: **fixtures sintéticas** apenas
- Import CLI lê path externo; não copia `.txt` para o repo

---

## 5. Ficheiros criados/alterados

| Ficheiro | Mudança |
|----------|---------|
| `kernel/memory/whatsapp_import.py` | Parser export WhatsApp |
| `kernel/memory/import_history.py` | CLI import + benchmark |
| `kernel/memory/group_memory.py` | mídia/apagadas, purge retention, BM25 skip deleted |
| `kernel/context/types.py` | `use_group_memory` em ContextRoute |
| `kernel/context/router.py` | sinal GROUP_MEMORY |
| `kernel/orchestrator/context.py` | gate router + max_chars + source_type |
| `kernel/config.py` | `KERNEL_GROUP_MEMORY_RETENTION_DAYS` |
| `tests/test_whatsapp_import.py` | testes sintéticos |
| `.gitignore`, `.dockerignore`, `.env.example` | privacidade + config |
| `data/.gitkeep`, `data/messages/.gitkeep` | estrutura vazia |

---

## 6. Importação do `.txt` real

**Estado:** importado em 2026-08-27 a partir de `Downloads/…Ponto Zero - Infnet 2026.1.txt` (ficheiro **fora do repo**).

| Métrica | Valor |
|---------|-------|
| `channel_id` | `120363408044356181@g.us` (JID Orbit — `exports/ponto-zero-infnet-2026-1-*.json`) |
| Linhas lidas | 18 684 |
| Mensagens parseadas | 17 155 |
| Gravadas SQLite | 17 061 |
| Sistema ignorado | 161 |
| Mídia | 1 327 |
| Apagadas (metadata) | 55 |
| Links (metadata) | 158 |
| Erros parse | 2 |
| Tempo parse | ~925 ms |
| Tempo insert | ~358 ms |
| Re-import idempotente | delta 0 (sem duplicar) |
| BM25 p95 (5 queries genéricas) | ~334 ms (1.ª busca inclui build índice) |

Comando:

```bash
python -m kernel.memory.import_history \
  --file "/caminho/privado/export.txt" \
  --platform whatsapp \
  --channel-id '120363408044356181@g.us' \
  --benchmark
```

**Importante:** `channel_id` deve coincidir com o JID que o Orbit envia em `context.channel_id` — senão mensagens novas e histórico ficam em canais diferentes.

---

## 7. Configuração nova

| Variável | Default | Descrição |
|----------|---------|-----------|
| `KERNEL_GROUP_MEMORY_ENABLED` | true | Liga store |
| `KERNEL_GROUP_MEMORY_DB_PATH` | data/group_memory.sqlite3 | Path SQLite |
| `KERNEL_GROUP_MEMORY_MAX_RESULTS` | 5 | Top-K histórico |
| `KERNEL_GROUP_MEMORY_RECENCY_WEIGHT` | 0.3 | Peso recência |
| `KERNEL_GROUP_MEMORY_MAX_CHARS` | 4000 | Budget prompt |
| `KERNEL_GROUP_MEMORY_RETENTION_DAYS` | 0 | 0 = sem purge auto |
| `ACL_CONTEXT_ROUTER` | false | Se 1, gate GROUP_MEMORY |

---

## 8. Limitações / próximos passos

- BM25 rebuild por canal é lazy (re-lê SQLite), não índice incremental on-disk
- Reply-to / quotes: metadata preparada; parser básico ainda não extrai citações
- Retention purge: método `purge_older_than()` — agendar via cron/ops manual
- Anexar `.txt` real para benchmark de import local
- Orbit: wire batch import pós-export se desejado

---

## 9. Testes

```bash
pytest tests/test_group_memory.py tests/test_whatsapp_import.py tests/test_group_endpoints.py -q
```
