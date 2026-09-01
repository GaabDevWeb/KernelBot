# Domain Experts — routing e scoped retrieval

## Conceito

**Domain Expert** não é um LLM nem um agente independente. É uma abstração leve que descreve:

- domínio de conhecimento (Python, SQL, Java, C#…);
- keywords e aliases para classificação;
- `retrieval_scope` — silos BM25 permitidos;
- instruções opcionais e mínimas (quando necessário).

Fluxo:

```
Mensagem → Domain Router → scoped BM25 → Context Builder → LLM atual
```

Objectivo: **reduzir o espaço de busca** antes do BM25, recuperar menos contexto irrelevante e manter latência/tokens ≤ baseline.

## Componentes

| Ficheiro | Papel |
|----------|--------|
| `kernel/context/domain_experts.json` | Configuração centralizada de experts e thresholds |
| `kernel/context/domain_router.py` | `DomainRouter.route()` — classificação determinística |
| `kernel/orchestrator/context.py` | Integração antes de `search_candidates()` |
| `kernel/rag/search.py` | `discipline_filters` para multi-silo scoped search |

## DomainExpert

Campos principais (adaptados ao JSON real):

- `id`, `name`
- `keywords`, `aliases`
- `retrieval_scope` — lista de silos (`disciplines.json` / MySQL)
- `instructions` — bloco curto opcional (≤ ~240 chars no router)

Keywords são enriquecidas automaticamente com `queryMarkers` das disciplinas no scope (SSOT `kernel/disciplines/disciplines.json`).

## Domain Router

**Sem LLM.** Combina:

1. termos da query (peso 1.0);
2. contexto recente WhatsApp (peso 0.35 — só sinal de classificação, não vira query RAG);
3. keywords + aliases + markers das disciplinas.

Scoring:

- contagem de hits + peso por comprimento do termo;
- softmax leve sobre scores normalizados → confiança 0–1;
- candidatos ordenados por score.

### Thresholds (`domain_experts.json`)

| Parâmetro | Default | Significado |
|-----------|---------|-------------|
| `threshold_single` | 0.35 | Confiança mínima para um único domínio |
| `threshold_multi` | 0.20 | Segundo colocado mínimo para multi-domain |
| `multi_gap` | 0.12 | Gap máximo entre 1.º e 2.º para activar multi |
| `min_raw_hits` | 1 | Hits mínimos por expert |

### Multi-domain

Quando top-2 experts estão próximos (ex.: Java 0.51 + SQL 0.47), o router activa `multi_domain` e passa **todos** os `retrieval_scope` relevantes via `discipline_filters`.

### Fallback global

Fallback quando:

- nenhum keyword hit;
- confiança abaixo do threshold;
- scope vazio (silos não indexados);
- scoped retrieval devolve zero candidatos (`scoped_empty_fallback`).

Nunca falha o request — degrada para BM25 global existente.

## Scoped retrieval

Um único índice BM25 por silo. O scope aplica-se **antes** da seleção:

```python
search_candidates(query, discipline_filter="python")           # single silo
search_candidates(query, discipline_filters=("python", "sql-modelagem-relacional"))  # multi
```

Não há segundo RAG, segundo BM25 nem vector DB.

## Relação com outros subsistemas

| Subsistema | Relação |
|------------|---------|
| **Context Router** (FAST/NORMAL/DEEP) | Orthogonal — controla camadas de prompt, não silo BM25 |
| **RAG / `build_decision`** | Inalterado — recebe candidatos já filtrados |
| **Group Memory** | Independente — expert não bloqueia memória de grupo |
| **Comandos `/python`, `/doc`** | Têm precedência — domain router só actua quando não há disciplina explícita |
| **Catálogo de aulas** | Pode estreitar disciplina antes do domain router |

## Configuração

- Ficheiro: `kernel/context/domain_experts.json`
- Flag: `ACL_DOMAIN_ROUTER` (default **off** — activar com `1`/`true`)

Experts iniciais (silos reais na KB):

- **python** → `python`, `python-processamento-dados`
- **sql** → `sql-modelagem-relacional`, `visualizacao-sql`
- **java** → `fundamentos-java`
- **csharp** → `fundamentos-csharp`

Adicionar expert = entrada JSON + silos existentes; sem alterar código.

## Observabilidade

`ContextTrace` expõe:

- `domain_candidates`, `selected_domain`, `domain_confidence`
- `domain_retrieval_scope`, `domain_fallback`, `domain_multi`
- `domain_router_reason`, `domain_router_latency_ms`

Painel `/traces` — secção **Domain Router** em `templates/traces/detail.html`.

## Futuro (não implementado)

A abstração `DomainExpert` permite, mais tarde, mapear `id` → modelo LLM específico. V1 **não** activa multi-model.

## Princípio

> Expert = routing + scoped retrieval, não multi-agent.

Medir sucesso por: menos candidatos considerados, menos tokens de contexto, latência estável ou menor — sem regressão de recall (fallback global cobre falhas de scope).
