# Plano True Kernel — Capability IR (texto)

feature_id: true-kernel
branch: trueKernel
docs: aprovado

## Objetivo
Kernel HTTP reutilizável sem UI; contratos POST /chat, POST /search, GET /health; lógica RAG/LLM preservada.

## Grafo

| ID | Descrição | Tipo | Depende | Aceite |
|----|-----------|------|---------|--------|
| TK-01 | Remover frontend/templates/deps UI/mounts/GET / | backend | — | sem HTML; factory sem static UI |
| TK-02 | Reorganizar engine+core → kernel/* | backend | TK-01 | imports kernel.*; engine/core removidos ou shims |
| TK-03 | Schemas Pydantic + Chat JSON + Search | backend | TK-02 | API_SPEC v1 cumprida |
| TK-04 | adapters/ placeholder + Docker/requirements/README | backend | TK-03 | imagem sem frontend |
| TK-05 | Suite pytest mínima | testing | TK-03 | pytest verde |
| TK-06 | Security + PO + docs entrega | gates | TK-05 | OK |

## Caminho crítico
TK-01 → TK-02 → TK-03 → TK-05

## Restrições SSOT
- Sem microserviços/Kafka/RabbitMQ
- Preservar lógica RAG/LLM
- Branch trueKernel only
