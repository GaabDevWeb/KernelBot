# Staging e testes locais

[← Índice](README.md) · Guia rápido: [TESTE-LOCAL.md](../../TESTE-LOCAL.md)

## Pré-requisitos

| Item | Nota |
|------|------|
| Docker | Grupo `docker` no utilizador (`usermod -aG docker`) |
| Python venv | Dependências do KernelBot instaladas |
| `.env.staging.local` | Credenciais MySQL `:3307` — **não commitar** |
| `OPENROUTER_API_KEY` | Em `.env` ou export |

## Dois passos (obrigatório)

### Passo 1 — Setup (terminal separado, uma vez)

```bash
cd /home/gaab/Documentos/gitHub/KernelBot
./bin/staging-setup.sh
```

Esperado: `E2E: SIM` no final (schema + seed + rebuild BM25).

### Passo 2 — Servidor (deixar a correr)

```bash
./bin/staging-serve.sh
```

Abrir: **http://127.0.0.1:8001**

| Erro | Causa | Fix |
|------|-------|-----|
| `ERR_CONNECTION_REFUSED` | Servidor não está up | `staging-serve.sh`, não `python main.py` só |
| Crash Aiven no boot | `.env` aponta prod | Usar `KERNELBOT_ENV=staging` via script |
| `Table knowledge doesn't exist` | Container antigo | `staging-apply-schema.sh` + setup |
| `source .env` quebra shell | API key com caracteres especiais | Script **não** faz `source .env` |

## Ingest ISS completo (opcional)

```bash
./bin/staging-ingest-iss.sh
```

Requer repo ISS no path esperado pelo script. Depois: restart ou `POST /reload`.

## Bateria de testes no chat

### Devem passar (retrieval + resposta)

| Pergunta | Notas |
|----------|-------|
| `transformers` | BM25 chunk 0 |
| `4 níveis de integridade` | Conteúdo legacy-modelagem |
| `diferença ML e DL` | fluencia-b2 |
| `IA generativa vs determinística` | — |

### Devem hard-stop (gates)

| Pergunta | `reason` esperado |
|----------|-------------------|
| `oi` | `underspecified_query` |
| Pergunta AT/TP fora do material | `insufficient_context` ou `index_gap` |
| `/python` sem aula python no índice | `index_gap` |
| Pergunta vaga tipo "performance" | `vague_but_high_risk` |

### Admin

| Comando | Requisito |
|---------|-----------|
| `/reload` | Header `X-Reload-Token` = `ACL_RELOAD_TOKEN` |

## Limitação do índice mínimo (2 aulas)

Com apenas `_staging/legacy-modelagem` e `_staging/fluencia-b2`:

- Muitas queries trazem **ambas** as fontes no rodapé.
- Não representa comportamento em produção com dezenas de silos.

## Disclaimer `post_generation_misalignment`

| Sintoma | Não é |
|---------|-------|
| Resposta boa + aviso no final | Falha de ingest B2 |
| Score 1.00 no rodapé | — |

É calibração de `post_generation_flags()` — ver [06-gates-e-decisoes.md](06-gates-e-decisoes.md).

## Health check

```bash
curl -s http://127.0.0.1:8001/health/catalog | jq .
```

## Smoke test de latência (UI + SSE)

Ver passos detalhados em [TESTE-LOCAL.md](../../TESTE-LOCAL.md#smoke-test-de-latência-browser). Resumo:

| Passo | O que valida |
|-------|----------------|
| Slow 3G no DevTools | `api.js` acumula `ACL_META` parcial; UI não assume meta completo no primeiro chunk |
| `ACL_DISAMBIGUATION_ENABLED=true` + query ambígua | Chips + strip de `<ambiguity_options>` |
| Resposta com flags pós-geração | Badge/hint reactivo (`post_generation_override`) |

## Ver também

- [12-configuracao.md](12-configuracao.md)
- [09-fluxos-operacionais.md](09-fluxos-operacionais.md)
- [08-frontend-ui.md](08-frontend-ui.md)
