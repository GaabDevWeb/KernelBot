# Frontend e UI

[← Índice](README.md)

## Stack UI

| Peça | Localização |
|------|-------------|
| Template | `templates/index.html` |
| Lógica | `frontend/src/ui.js`, `main.js` |
| API SSE | `frontend/src/api.js` |
| Sessão | `frontend/src/utils/sessionId.js` |
| Estilos | `frontend/assets/css/theme.css` |

## Fluxo do chat (browser)

```mermaid
sequenceDiagram
  participant U as Utilizador
  participant UI as ui.js
  participant API as api.js
  participant S as KernelBot /chat
  U->>UI: Envia mensagem
  UI->>API: streamChat()
  API->>S: POST JSON
  S-->>API: SSE ACL_META
  API-->>UI: onMeta(decision)
  alt allow_generation
    S-->>API: tokens
    API-->>UI: onToken
  else hard stop
    S-->>API: mensagem fixa
  end
  API-->>UI: onDone
```

## Contrato UI ↔ `ACL_META` (v=3)

Campo canónico: **`allow_generation`** (boolean). O frontend também aceita fallback legado: `decision === "answer"` ⇒ geração permitida.

| `reason` | `allow_generation` | `decision` | UI |
|----------|-------------------|------------|-----|
| `ok` | `true` | `answer` | Stream markdown + breadcrumbs de fontes |
| `ambiguous_retrieval` | `true` | `answer` | Stream markdown + badge informativo (sem chips) |
| `ambiguous_retrieval` | `false` | `hard_stop` | `DisambiguationChips` ou texto fixo; `onDelta` ignorado |
| `index_gap` | `false` | `hard_stop` | `IndexGapAlert` |
| Outros hard stops | `false` | `hard_stop` | Texto fixo streamed (sem LLM) |

Regra implementada em `frontend/src/acl/parseAclMeta.js`: UI estruturada (chips, index gap) **só** quando `allowsGeneration(meta) === false`. Com `ACL_DISAMBIGUATION_ENABLED=true`, `ambiguous_retrieval` envia `allow_generation: true` e não monta chips — evita colisão chips + tokens SSE.

### Smoke manual (browser)

1. `ACL_DISAMBIGUATION_ENABLED=false` — pergunta ambígua com 2+ hits próximos → chips ou mensagem fixa, sem markdown longo do modelo.
2. `ACL_DISAMBIGUATION_ENABLED=true` — mesma pergunta → resposta em markdown com stream; badge “Várias fontes próximas…” nos breadcrumbs; sem `.disambiguation-chips`.
3. Pergunta com match claro → stream normal, sem badge de desambiguação.

## Componentes por `reason` (hard stop)

| Componente | Ficheiro | Quando |
|------------|----------|--------|
| `IndexGapAlert` | `components/IndexGapAlert.js` | `index_gap` + `allow_generation=false` |
| `DisambiguationChips` | `components/DisambiguationChips.js` | `ambiguous_retrieval` + `allow_generation=false` + `payload.suggested_candidates` |

## ACL meta no rodapé

A UI mostra (quando disponível):

- Score de confiança
- Fontes (`db:...`)
- Termos correspondidos
- Aviso `post_generation_misalignment`

## Parse de ACL (`frontend/src/acl/parseAclMeta.js`)

| Função | Papel |
|--------|-------|
| `allowsGeneration` | Lê `allow_generation` ou infere de `decision` |
| `isStructuredHardStop` | `index_gap` / `ambiguous_retrieval` sem geração |
| `shouldMountDisambiguationChips` | Chips bloqueantes |
| `isDisambiguationGeneration` | Badge informativo no stream |

## Sessão

| Aspecto | Implementação |
|---------|---------------|
| ID | UUID em `sessionStorage` |
| Pin | Servidor-side `PinnedSessionStore` por `session_id` |
| TTL pin | `ACL_PIN_TTL_TURNS` (default 3) |

## Markdown na resposta

Renderização client-side das mensagens do assistente (biblioteca conforme `ui.js`).

## Ver também

- [07-apis-e-sse.md](07-apis-e-sse.md)
- [06-gates-e-decisoes.md](06-gates-e-decisoes.md)
