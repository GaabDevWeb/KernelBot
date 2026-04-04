# ACL — Agente de Contexto Local

## O que é o ACL?

O ACL (Agente de Contexto Local) é um chatbot RAG de alta performance desenvolvido com FastAPI. Ele indexa arquivos Markdown desta pasta (`/content`) em memória usando BM25 e injeta o contexto relevante no prompt antes de cada chamada à LLM.

## Como funciona o BM25?

BM25 (Best Match 25) é um algoritmo de ranking probabilístico que calcula a relevância de um documento para uma query. Diferente da busca vetorial, o BM25 não precisa de GPU nem de embeddings — é puramente estatístico e extremamente rápido.

A fórmula considera:
- **TF (Term Frequency)**: quantas vezes o termo aparece no documento
- **IDF (Inverse Document Frequency)**: quão raro o termo é na coleção
- **Normalização por tamanho**: documentos longos não penalizam artificialmente

## Como usar o /content

Prefixe sua mensagem com `/content` para forçar a injeção do contexto da base de conhecimento, independente do score BM25. Exemplo:

```
/content quais são os arquivos disponíveis?
/content explique o que é BM25
```

Sem o prefixo, o ACL só injeta contexto se o score de relevância for > 0.7.

## Streaming SSE

O backend retorna respostas via Server-Sent Events (SSE). Cada token gerado pela LLM é enviado imediatamente para o frontend, que renderiza o Markdown parcial em tempo real.

## Watchdog

O sistema monitora a pasta `/content` em tempo real. Ao salvar ou criar um arquivo `.md`, o índice BM25 é reconstruído automaticamente em background sem reiniciar o servidor.

## Adicionando conhecimento

1. Crie um arquivo `.md` nesta pasta (`/content/`)
2. O índice será atualizado automaticamente em ~1.5 segundos
3. Faça uma pergunta — o ACL usará o novo conteúdo como contexto
