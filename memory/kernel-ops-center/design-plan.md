# Design plan — Kernel Ops (frontend-pro Build)

## Direção
Painel operacional (não landing). Signature: **sidebar escura slate** + conteúdo claro com accent cyan `#0284c7`.

## Anti-slop
- Evitado cream/serif/terracotta e purple-glow SaaS
- Tipografia: Source Sans 3 + IBM Plex Mono
- Cards só para KPIs e painéis de dados
- Gráficos SVG server-side (sem lib pesada)

## Viewports
Mobile: sidebar empilha no topo (`max-height: 40vh` scroll). Desktop: shell flex.
