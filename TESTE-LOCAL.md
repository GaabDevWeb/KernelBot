# Testar KernelBot localmente (staging)

Ambiente com MySQL em Docker (porta **3307**). O teu `.env` de produção (Aiven) **não é alterado**.

## Pré-requisitos

- Docker (utilizador no grupo `docker`, ou `sudo` nos comandos abaixo)
- Python 3 + `.venv` (criado pelo setup)
- `.env` no KernelBot com chave LLM (`OPENROUTER_API_KEY` ou `CURSOR_API_KEY` conforme `ACL_LLM_PROVIDER`)
- `.env.staging.local` (copia de `.env.staging.example`)

## Passo a passo (2 terminais)

**Terminal 1 — dados (uma vez):**

```bash
cd /home/gaab/Documentos/gitHub/KernelBot
chmod +x bin/*.sh
./bin/staging-setup.sh
```

O setup sobe MySQL staging, aplica o schema `knowledge`, e ingere a wiki em `discipline=doc` via `bin/ingest-wiki-doc.sh`.

**Terminal 2 — servidor (deixar aberto):**

```bash
cd /home/gaab/Documentos/gitHub/KernelBot
./bin/staging-serve.sh
```

Abre o browser **só quando** o terminal mostrar `Uvicorn running on http://127.0.0.1:8001`:

http://127.0.0.1:8001

**Não uses** `python main.py` directo sem `KERNELBOT_ENV=staging` — lê o Aiven do `.env`, falha ao ligar ou aponta para produção por engano.

**`comando não encontrado` ao correr staging-serve** — o `.env` tem linhas que o bash não consegue interpretar com `source`. Usa sempre `./bin/staging-serve.sh` (não faz `source .env` no bash; LLM keys vêm do Python via dotenv).

## Smoke do silo `/doc`

Ver [`PERGUNTAS-SMOKE-DOC-WIKI.md`](PERGUNTAS-SMOKE-DOC-WIKI.md) — 30 perguntas com protocolo:

1. **Nova conversa** antes de cada pergunta (não só `/reset`).
2. Aguardar badge **Online** e `data: [DONE]` antes da seguinte.
3. Prefixo `/doc` em cada mensagem.

Após editar ficheiros em `docs/wiki/`, re-ingest:

```bash
KERNELBOT_ENV=staging ./bin/ingest-wiki-doc.sh
# reiniciar staging-serve ou POST /chat com message=/reload + Bearer
```

## Testes rápidos no chat

| Teste | Pergunta sugerida |
|-------|------------------|
| Wiki doc | `/doc O que é o KernelBot?` |
| Fontes doc | `/doc Quais comandos posso usar no início da mensagem?` |

## Checklist grounding `anchored` (default)

Com `ACL_GROUNDING_POLICY=anchored` no `.env` (ou omitido — default em código):

1. **On-corpus** (`reason=ok`): resposta cita `[Fonte: …]` e pode incluir bloco *Extensão pedagógica* sem override `post_generation_misalignment`.
2. **Off-corpus** (pergunta fora do índice, 2+ termos): aviso de lacuna — sem inventar comandos do ACL.
3. **Desambiguação:** chips só com `ACL_DISAMBIGUATION_ENABLED=true`; com `false`, `ambiguous_retrieval` gera texto sem chips automáticos.

## O que o setup faz

1. **Docker** — `kernelbot-mysql-staging` na porta `3307`
2. **Schema** — tabela `knowledge` via `docker/init-knowledge.sql`
3. **Ingest wiki** — páginas `docs/wiki/*.md` → `discipline=doc`

## Ingestão ISS completa (opcional)

Para carregar aulas do ISS no MySQL staging:

```bash
./bin/staging-ingest-iss.sh
./bin/staging-serve.sh   # reinicia o bot
```

## Parar

```bash
docker stop kernelbot-mysql-staging
# ou:
# docker compose -f docker-compose.staging.yml down
```

## Ficheiros

| Ficheiro | Função |
|----------|--------|
| `.env.staging.local` | DB local (3307) |
| `docker-compose.staging.yml` | MySQL Docker |
| `bin/staging-setup.sh` | Setup automático |
| `bin/staging-serve.sh` | Bot + UI com DB staging |
| `bin/ingest-wiki-doc.sh` | Wiki → MySQL `doc` |
| `docker/init-knowledge.sql` | Schema `knowledge` |

## Problemas comuns

**`permission denied` no Docker** — adiciona o teu user ao grupo docker:

```bash
sudo usermod -aG docker "$USER"
newgrp docker   # ou logout/login
```

**`Table 'kernelbot_staging.knowledge' doesn't exist`:**

```bash
./bin/staging-apply-schema.sh
./bin/staging-setup.sh
```

**`Connection refused` na porta 3307** — corre `./bin/staging-setup.sh` de novo.

**Chave LLM ausente** — preenche o `.env` principal conforme `ACL_LLM_PROVIDER`.

**Chat sem resposta / hard stop** — queries de **uma palavra** podem falhar nos gates (`ACL_RETRIEVAL_MIN_TERMS=2`). Usa 2+ termos.

## Testes automatizados

```bash
cd /home/gaab/Documentos/gitHub/KernelBot
PYTHONPATH=. .venv/bin/pytest tests/ -q
```
