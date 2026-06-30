# UI Canonical Layout — KernelBot

Documento de arquitetura visual. **Regra zero:** o composer é a fonte canônica do contexto da conversa.

Antes de adicionar qualquer elemento de UI, responder: *qual região é dona disso?*

---

## Regiões

### Header

**Responsabilidade:** Navegação e chrome global.

- Toggle / acesso a conversas (mobile)
- Nova conversa
- Configurações (quando existirem)
- Estado do sistema (Online — se mantido)

**Nunca contém:**

- Disciplina ativa *(exceto exceção landing)*
- Pin de aula
- Contexto da conversa corrente como controle editável
- Badges transitórios de turno
- Modelo LLM ou meta técnica do turno

**Exceção landing:** `#active-discipline-badge` permitido **somente** enquanto `#empty-state` estiver visível.

**Exceção wayfinding (sidebar colapsada ou ChatActive):** `#header-conversation-label` — rótulo **read-only** do título da conversa ativa (truncado, `title` com texto completo). Orientação de navegação; **não** substitui o composer como fonte de contexto editável.

---

### Chat

**Responsabilidade:** Histórico e conteúdo gerado.

- Mensagens user / bot
- Streaming e cursor
- Markdown renderizado
- Fontes e breadcrumbs da resposta (read-only, colapsável)
- Chips de desambiguação dentro do turno

**Nunca contém:**

- Controles que alteram o próximo envio
- Disciplina ativa como controle
- Pin editável

---

### Composer

**Responsabilidade:** Tudo que influencia a **próxima** mensagem.

- Textarea, botão enviar
- Scope / disciplina (`#scope-btn`, silo-pill, `context-stack`)
- Pin de aula (`context-pin-badge`)
- Slash menu e autocomplete
- Trigger do painel de disciplina (scope-btn ou silo-pill)

**Nunca contém:**

- Histórico de mensagens
- Lista de conversas

---

### Sidebar

**Responsabilidade:** Navegação entre conversas.

- Lista, busca, nova conversa, colapso
- Título da conversa (metadado de sessão)

**Nunca contém:**

- Disciplina ativa, pin ou contexto de escopo da conversa corrente

---

## Estados da UI

| Estado | Condição | Header | Hero | Composer |
|--------|----------|--------|------|----------|
| **Landing** | `#empty-state` visível | Badge disciplina OK | Visível | Contexto OK |
| **ChatActive** | ≥1 mensagem no chat | Sem badge disciplina | Hidden | Único source of truth |

**Transições:**

- `Landing → ChatActive`: primeira mensagem enviada
- `ChatActive → Landing`: nova conversa / reset

---

## Regra de ouro

1. Influencia a próxima mensagem? → **Composer**
2. É global à app? → **Header**
3. É histórico? → **Chat**
4. É troca de sessão? → **Sidebar**

Se a resposta não for única, o elemento não entra até o conflito ser resolvido neste documento.

---

## Implementação (referência de código)

- Estado UI: [`frontend/src/utils/uiState.js`](../frontend/src/utils/uiState.js) — `isLanding()`, `isChatActive()`, `syncBodyUiState()`
- Rótulo header: [`frontend/src/utils/headerLabel.js`](../frontend/src/utils/headerLabel.js) — `#header-conversation-label`
- Refresh disciplina: [`frontend/src/chat/ComposerController.js`](../frontend/src/chat/ComposerController.js)
- Pin: [`frontend/src/chat/MetaRenderer.js`](../frontend/src/chat/MetaRenderer.js)
- Painel disciplina: abre via scope-btn / silo-pill, não via header em ChatActive
- Toast / undo: [`frontend/src/utils/toast.js`](../frontend/src/utils/toast.js)
- Sidebar conversas: [`frontend/src/components/ConversationSidebar.js`](../frontend/src/components/ConversationSidebar.js) — delete, rename, colapso
- Streaming / stop: [`frontend/src/components/Composer.js`](../frontend/src/components/Composer.js), [`frontend/src/chat/StreamController.js`](../frontend/src/chat/StreamController.js)
- Toolbar mensagem: [`frontend/src/components/MessageRow.js`](../frontend/src/components/MessageRow.js) — copiar, regenerar
- Markdown ACL: [`frontend/src/utils/markdown.js`](../frontend/src/utils/markdown.js) — disclaimer colapsável, copy em `pre`
- Scroll FAB: [`frontend/src/components/ChatView.js`](../frontend/src/components/ChatView.js)
- Atalhos: [`frontend/src/components/ShortcutsOverlay.js`](../frontend/src/components/ShortcutsOverlay.js) — `?`, `Ctrl+/`
- Motion landing↔chat: [`frontend/src/components/ChatView.js`](../frontend/src/components/ChatView.js), [`frontend/src/entrance.js`](../frontend/src/entrance.js)

### Tokens CSS relevantes (`theme.css`)

| Token | Uso |
|-------|-----|
| `--shell-max-chat` | Largura máxima do shell em ChatActive (`min(1400px, 100%)`) |
| `--chat-read-max` | Coluna de leitura bot + composer alinhado |
| `--surface-user` | Superfície das mensagens do utilizador |
| `--btn-streaming` | Botão enviar durante geração |
| `--toast-z` | Z-index do toast |
