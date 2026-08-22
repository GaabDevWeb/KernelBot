# ADR-0001: True Kernel monólito com API universal (sem frontend)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-24 |
| Status | accepted |
| Deciders | MegaBrain + missão utilizador |

## Contexto

O KernelBot entrega valor educacional no backend (RAG + LLM), mas o processo FastAPI também monta UI estática, templates Jinja2 e CSP de browser. Isso impede reutilização limpa por canais não-web e confunde o produto (UI vs núcleo).

Restrições da missão: **não** criar microserviços; **não** introduzir Kafka/RabbitMQ; preservar lógica validada; priorizar simplicidade.

## Decisão

Transformamos o repositório num **monólito Kernel + API HTTP**:

1. Remover completamente a camada de apresentação web do runtime.
2. Reorganizar o domínio em pacote `kernel/` (ou mapeamento equivalente a partir de `engine/` + `core/`) e expor `api/` fina.
3. Adoptar **contrato JSON universal** como interface pública canónica.
4. Manter um único processo FastAPI/Uvicorn.
5. Deixar `adapters/` como fronteira futura (sem implementação de canais nesta entrega).
6. Trabalho exclusivo na branch `trueKernel`.

## Alternativas consideradas

### Alternativa A — Extrair UI para repositório separado e manter KernelBot como “app web”

- Prós: UI continua a evoluir no ecossistema actual.
- Contras: produto continua centrado em web; não cumpre “produto = Kernel”; custo de coordenação multi-repo sem benefício imediato.

### Alternativa B — Microserviços (API gateway + RAG service + LLM service)

- Prós: escala independente teórica.
- Contras: proibido pela missão; complexidade operacional desproporcional ao tamanho actual.

### Alternativa C — Manter SSE como único contrato e só remover UI

- Prós: menos mudança no protocolo.
- Contras: adapters mobile/LMS preferem JSON; SSE + `[ACL_META]` acopla clientes ao frontend legado.

### Alternativa D — (escolhida) Monólito Kernel + JSON canónico + stream opt-in

- Prós: alinhado à missão; reutilizável; mudança controlada; preserva providers/streaming internos.
- Contras: clientes SSE legacy precisam migrar ou usar modo stream; rename de pacotes exige cuidado com imports.

## Consequências

### Positivas

- Kernel consumível por qualquer plataforma via HTTP
- Fronteira clara: Kernel não conhece HTML/CSS/JS de UI
- Deploy mais leve (sem assets frontend)
- Contrato estável para futuros adapters

### Negativas / trade-offs

- Breaking change para quem dependia de `GET /` e SSE default
- Esforço de reorganização de pastas e docs wiki
- Necessidade de recriar suite `tests/` ausente

## Referências

- PRD: `docs/prd/2026-07-24-true-kernel.md`
- API: `docs/API_SPEC.md`
- Arquitectura: `docs/ARCHITECTURE.md`
