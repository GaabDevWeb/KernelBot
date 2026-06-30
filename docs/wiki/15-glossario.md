# Glossário

[← Índice](README.md)

| Termo | Definição |
|-------|-----------|
| **ACL** | Agente de Contexto Local — este projeto (KernelBot). |
| **BM25** | Algoritmo léxico de ranking (`rank_bm25.BM25Okapi`). |
| **Silo** | Índice BM25 isolado por `discipline`. |
| **Chunk** | Janela de texto indexada em RAM (~500 palavras, overlap 50). |
| **Opção B** | Documento unificado no MySQL; chunking só no KernelBot. |
| **Opção B2** | Meta léxico apenas no `chunk_index == 0`. |
| **Bloco meta** | Cabeçalho `[CONCEITOS E KEYWORDS…]` até `====== FIM DOS METADADOS ======`. |
| **Hard stop** | Recusa de gerar LLM; mensagem pedagógica fixa. |
| **Gate** | Regra em `build_decision()` ou `post_generation_flags()`. |
| **`raw_score`** | Score BM25 antes de normalizações de UI. |
| **`source`** | Identificador `db:{discipline}/{slug}`. |
| **Pin** | Chunks fixados por `session_id` por N turnos. |
| **`index_gap`** | Aula no catálogo ISS mas ausente do índice MySQL/RAM. |
| **Fase 5b** | Pipeline ISS: validate → ingest → verify/reload. |
| **ISS** | Repositório de conteúdo pedagógico (markdown + jsons). |
| **Job 2** | Ingest Python `ingest-knowledge.py`. |
| **Job 3** | Verify + reload KernelBot. |
| **`ACL_META`** | Evento SSE v=3 com metadados da decisão. |
| **IDF** | Inverse document frequency — penaliza termos em muitos docs do silo. |
| **Drift** | Divergência catálogo ↔ chaves indexadas. |
| **Staging** | Ambiente local MySQL Docker + `KERNELBOT_ENV=staging`. |
| **Recomendação A** | Não re-injectar meta no prompt quando só chunks ≥1. |
| **`post_generation_misalignment`** | Override pós-LLM por heurística conservadora. |
