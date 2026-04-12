---
name: explicar-projeto-kernelbots
description: Explains KernelBots (ACL) architecture, flows, and concepts by reading documentation.md and source files without writing or changing code. Use when the user asks how something works, why a piece of code exists, wants doubts clarified, onboarding explanations for juniors, or conceptual walkthroughs of RAG, BM25 silos, SSE, context pinning, API contracts, or frontend-backend links.
---

# Explicar projeto KernelBots (ACL)

## Propósito

Esta skill orienta o agente a **esclarecer dúvidas sobre o projeto** em modo **somente leitura**: ler ficheiros, cruzar com a documentação e **explicar** — **não** implementar, refatorar nem propor patches, salvo se o utilizador pedir explicitamente código noutro contexto.

## Fontes (ordem sugerida)

1. **`documentation.md`** na raiz do repositório — visão consolidada (propósito, arquitetura, APIs, fluxos, glossário, registo de alterações). Consultar primeiro para alinhar nomes e decisões já documentadas.
2. **Código e configs** — `main.py`, `core/`, `engine/`, `api/`, `app/`, `frontend/`, `templates/`, `tests/`, `README` se existir, para amarrar explicações a ficheiros e funções reais.
3. **`content/doc/`** — pode conter cópias ou material de corpus; se a dúvida for “o que está no índice doc”, distinguir **documentação de produto** (raiz) de **ficheiros indexados** em `content/`.

## O que não fazer

- Não alterar ficheiros de código, estilos, templates nem configs como parte desta skill.
- Não “corrigir” o projeto; se houver discrepância doc vs código, descrever o que o código faz e assinalar a divergência.
- Não assumir APIs ou env vars não referenciadas no repo; citar onde viu cada afirmação.

## Estilo de explicação (nível estagiário com bases)

- **Começar pelo “para quê”**: uma frase sobre o objetivo do módulo ou fluxo antes dos detalhes.
- **Definir termos na primeira menção** (ex.: RAG, BM25, SSE, silo, `BuildMessagesResult`) em linguagem simples; depois usar o termo com confiança.
- **Seguir o caminho dos dados**: entrada (HTTP, ficheiro, evento) → módulos tocados → saída (resposta, stream, estado).
- **Explicar o “porquê”**: decisões de desenho (locks, debounce, thresholds, modos `ACL_GLOBAL_CONTEXT`) ligadas ao problema que evitam.
- **Ligar ao resto**: “isto chama X”, “é consumido por Y”, “configura-se em Z”.
- **Estrutura clara**: títulos curtos, listas quando ajudar, um diagrama em texto ou Mermaid só se o fluxo for ramificado.

## Estrutura típica de resposta

1. Resposta direta à pergunta (1–3 frases).
2. Contexto no sistema (onde vive no código e na doc).
3. Passo a passo ou fluxo, com referências a ficheiros/campos relevantes (formato de citação do projeto: blocos com caminho e linhas quando útil).
4. Glossário mini ou nota de edge cases se fizer sentido.

## Quando a doc e o código divergirem

Indicar ambos os estados, qual parece autoritativo (geralmente o código em runtime) e sugerir que a doc pode precisar atualização — **sem** editar ficheiros nesta skill.

## Gatilhos internos

Aplicar esta skill quando o pedido for: entender lógica, razão de existir de um ficheiro/função, fluxo end-to-end, conceitos (RAG, pinning, comandos `/doc`, disciplinas), integração frontend–backend, ou dúvidas de onboarding — sempre com foco em **explicação escrita**, não em implementação.
