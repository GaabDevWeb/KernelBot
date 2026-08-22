# Kernel Ops — Evolução visual (REPORT)

**Data:** 2026-07-29  
**Âmbito:** só UI/UX (Jinja/CSS/JS mínimo)  
**Restrição cumprida:** sem alteração de APIs, contratos, DB, remoção de rotas ou funcionalidades.

---

## 1. Auditoria do estado anterior

| Problema | Impacto |
|----------|---------|
| Ops CSS claro / “admin genérico” | Parecia painel corporativo, não Operator Console |
| Traces com tema claro + gradient | Inconsistente com dark-first pedido |
| Sem Command Palette | Navegação lenta entre ~25 destinos |
| Sidebar sem busca / ícones inconsistentes | Densidade e foco fracos |
| Sem breadcrumb no workspace | Orientação fraca |
| Dashboard com cards “executivos” | Pouca densidade operacional |
| Logs sem chips rápidos / vista terminal | Fluxo de triage mais lento |
| Playground linear (só resposta) | Menos “AI playground” moderno |

---

## 2. Design System

Documento: [`design-system/MASTER.md`](../../design-system/MASTER.md)

- Paleta `#09090B` / `#111113` / accent `#6366F1`
- Tipografia Inter + JetBrains Mono
- Componentes documentados (shell, cards densos, cmdk, lab-split, drawer)

---

## 3. Alterações realizadas

### Shell Ops
- `templates/ops/styles.css` — tokens dark-first completos
- `templates/ops/base.html` — topbar + breadcrumb + shell CmdK
- `templates/ops/_sidebar.html` — busca, ícones SVG, nav Linear-like
- `templates/ops/ops.js` — Command Palette (`Ctrl/⌘+K`), destinos de todos os módulos
- Breadcrumbs (`{% block crumb %}`) nas páginas Ops

### Páginas polidas
- `dashboard.html` — grelha métrica densa (msgs, users, erros, P95/P99, CPU, RAM, uptime)
- `logs.html` — chips All/Error/Warning/Info + painel terminal
- `login.html` — dark, alinhado ao shell
- `lab/playground.html` — split Prompt | Resposta + métricas
- `adapters/whatsapp.html` — indicador online/offline discreto

### Traces (mesmo contrato)
- `templates/traces/styles.css` — dark alinhado ao Ops
- `templates/traces/list.html` — drawer lateral (iframe do detalhe existente); **deep link `/traces/{id}` mantido**; Ctrl/⌘-click abre página

### Docs
- `design-system/MASTER.md`
- Este REPORT

---

## 4. Critérios de sucesso

| # | Critério | Estado |
|---|----------|--------|
| 1 | Funcionalidades existentes | Preservadas |
| 2 | Nenhuma rota removida | OK |
| 3 | Nenhuma API alterada | OK |
| 4 | Visual moderno Operator Console | Dark shell + CmdK |
| 5 | Lembra Linear/Obsidian/Cursor | Tokens + densidade |
| 6 | Navegação mais rápida | CmdK + busca sidebar |
| 7 | Densidade de informação | Cards 1px grid |
| 8 | Continua leve | Sem libs novas |
| 9 | Experiência operacional | Logs/chips, drawer traces |
| 10 | Não parece admin genérico | Tema + tipografia |

---

## 5. Como validar

1. Hard refresh em `http://127.0.0.1:8001/ops/login`
2. Entrar → Dashboard dark + sidebar
3. `Ctrl+K` → ir para Logs / RAG / Campanhas
4. Logs → chips Error
5. Traces → clique numa linha → drawer; “Abrir página” = detalhe completo
6. Playground → layout split

---

## 6. Follow-ups (UI only, sem backend)

- Ícones por grupo de nav (mapa SVG por `item.id`)
- Highlight de termos na Busca/RAG
- Drawer nativo (partial HTML) em vez de iframe, se/quando houver partial sem mudar contratos JSON
- Self-host Geist + Inter (remover CDN Google Fonts)
- Screenshots QA em `.frontend-review/` (matriz 1440/1920)
