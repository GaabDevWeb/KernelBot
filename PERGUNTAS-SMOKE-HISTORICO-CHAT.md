# Smoke — histórico de conversa (memória multi-turno)

Bateria mínima para validar a feature **histórico de conversa** (POC): persistência no browser, envio de `history` no `POST /chat` e continuidade do diálogo no LLM.

Use no browser (http://127.0.0.1:8001 em staging).

**Antes:** `./bin/staging-serve.sh` · hard refresh após deploy da branch `feature/chat-history-poc` (ou equivalente).

**Como marcar:** ✅ passou · ⚠️ aceitável · ❌ falhou · anotar se o modelo «lembrou» sem repetir a pergunta inteira.

**Legenda de perfil:** Estudante · Follow-up · Meta-conversa

---

## Índice

1. [Sequência smoke (3 turnos)](#sequência-smoke-3-turnos)
2. [Variantes opcionais](#variantes-opcionais)
3. [Checklist por turno](#checklist-por-turno)
4. [Critério de sucesso](#critério-de-sucesso)
5. [Referências](#referências)

---

## Sequência smoke (3 turnos)

Use na **mesma sessão**, **sem recarregar a página** entre os turnos 1–3. Não use `/reset` até terminar a sequência.

| # | Envie exactamente | Perfil | O que deve acontecer |
|---|-------------------|--------|----------------------|
| **H1** | `/python Me explica variáveis em Python com um exemplo de cadastro usando o nome Ana e a idade 25` | Estudante | Resposta sobre variáveis/tipos; exemplo coerente com **Ana** e **25**; `[Fonte:]` de Python; pin/silo Python |
| **H2** | `E o que é f-string?` | Follow-up | Resposta sobre f-string **sem** pedir de novo «variáveis» ou «Ana»; tom de continuação; liga ao exemplo anterior se fizer sentido; **sem** advisory amarelo espúrio |
| **H3** | `Qual nome e idade usei no meu primeiro exemplo desta conversa?` | Meta-conversa | Deve recordar **Ana** e **25** (ou equivalente explícito do turno H1); se não souber, lacuna honesta — **não** inventar outro nome |

### Sinais de que o histórico funciona (H3)

| Sinal | Esperado |
|-------|----------|
| Texto da resposta | Menciona Ana e 25 (ou reformula claramente a partir do turno 1) |
| Sem colar pergunta H1 de novo | Utilizador não precisou repetir o enunciado completo |
| RAG intacto | Ainda pode citar `[Fonte: db:python/…]` no H2/H3 |

### Sinais de falha (histórico não chegou ao LLM)

| Sinal | Interpretação |
|-------|----------------|
| H3: «não tenho registo da conversa anterior» | `history` não enviado ou não mergeado no backend |
| H3: inventa «João» / «30» | Modelo alucinou — falha pedagógica; verificar se H1 chegou no prompt |
| H2: responde só «o que são variáveis?» | Follow-up tratado como pergunta isolada (vaga) |
| Após F5 no meio da sequência | H3 falha mas H1–H2 visíveis na UI → bug de reenvio de `history` após reload |

---

## Variantes opcionais

Correr **depois** da sequência principal ou em sessão separada.

| Variante | Passos | O que validar |
|----------|--------|----------------|
| **V1 — Reload** | H1 → H2 → **F5 (hard refresh)** → H3 | UI repinta histórico (`localStorage`); H3 ainda acerta Ana/25 |
| **V2 — Nova conversa** | Completar H1–H3 → botão **Nova conversa** ou `/reset` → repetir H3 | H3 **não** deve lembrar Ana/25; chat limpo |
| **V3 — DevTools** | Durante H2, aba Network → `POST /chat` → Request payload | Campo `history` presente com turnos user/assistant anteriores; `message` = texto de H2 apenas |

---

## Checklist por turno

```text
#___  Turno H___  Mensagem: ___________
      Resposta referencia turno(s) anterior(es)? [ ] sim [ ] não [ ] N/A
      history no POST (V3)? [ ] sim [ ] não [ ] não verificado
      localStorage acl_conversation_v1 (Application)? [ ] sim [ ] não
      UI mostra turnos anteriores após F5? [ ] sim [ ] não [ ] N/A
      [Fonte: …] mantido? [ ] sim [ ] não
      Advisory amarelo indevido? [ ] sim [ ] não
      Pin / scope_hint (esperado só se mudar silo)? ___________
```

---

## Critério de sucesso

| Área | Mínimo aceitável |
|------|------------------|
| **H1** | Resposta pedagógica com Ana/25 e fontes Python |
| **H2** | f-string explicada como follow-up; não trata como pergunta vazia |
| **H3** | Ana + 25 corretos **ou** lacuna explícita (nunca inventar) |
| **V1 (opcional)** | Após reload, H3 ainda passa |
| **V2 (opcional)** | Nova conversa apaga memória de Ana/25 |
| **Regressão** | Pin, `[Fonte:]`, recusa de jailbreak **não** regressam (smoke em [PERGUNTAS-SMOKE-ESCOPO-PIN.md](PERGUNTAS-SMOKE-ESCOPO-PIN.md) #1–4) |

**Veredito da feature:** ✅ **3/3 turnos** conforme tabela + **V2** OK. ⚠️ H3 falha após V1 mas passa sem reload. ❌ H2 ou H3 ignoram H1 de forma consistente.

---

## Referências

| Documento | Uso |
|-----------|-----|
| [PERGUNTAS-SMOKE-ESCOPO-PIN.md](PERGUNTAS-SMOKE-ESCOPO-PIN.md) | Smoke pin/escopo/advisory (complementar) |
| [docs/wiki/07-apis-e-sse.md](docs/wiki/07-apis-e-sse.md) | Campo `history` no `POST /chat` |
| [TESTE-LOCAL.md](TESTE-LOCAL.md) | Subir staging |

**Última revisão:** junho/2026 — smoke histórico POC (3 turnos + 3 variantes opcionais).
