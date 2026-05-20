# Testar KernelBot + Opção B2 localmente

Ambiente **offline** com MySQL em Docker (porta **3307**). O teu `.env` de produção (Aiven) **não é alterado**.

## Pré-requisitos

- Docker (utilizador no grupo `docker`, ou `sudo` nos comandos abaixo)
- Python 3
- Repositório ISS em `../ISS` (já tens)
- `.env` no KernelBot com `OPENROUTER_API_KEY` (para o chat responder)

## Passo a passo (2 terminais)

**Terminal 1 — dados (uma vez):**

```bash
cd /home/gaab/Documentos/gitHub/KernelBot
chmod +x bin/*.sh
./bin/staging-setup.sh    # deve terminar com E2E: SIM
```

**Terminal 2 — servidor (deixar aberto):**

```bash
cd /home/gaab/Documentos/gitHub/KernelBot
./bin/staging-serve.sh
```

Abre o browser **só quando** o terminal mostrar `Uvicorn running on http://127.0.0.1:8001`:

http://127.0.0.1:8001

**Não uses** `python main.py` direto — lê o Aiven do `.env`, falha ao ligar e **não abre** a porta → `ERR_CONNECTION_REFUSED`.

**`comando não encontrado` ao correr staging-serve** — o `.env` tem linhas que o bash não consegue interpretar com `source`. Usa sempre `./bin/staging-serve.sh` actualizado (não faz `source .env`).

No chat, escolhe disciplina **`_staging`** (se o UI filtrar) ou pergunta em modo global:

| Teste | Pergunta sugerida |
|-------|------------------|
| Aula legada (sem meta) | `Quais são os quatro níveis de integridade do modelo relacional?` |
| Keyword B2 (chunk 0) | `transformers` ou `O que são transformers em IA generativa?` |

## O que o setup faz

1. **Docker** — `kernelbot-mysql-staging` na porta `3307`
2. **Seed** — 2 linhas em `knowledge`:
   - `_staging/legacy-modelagem` — markdown antigo **sem** bloco de metadados
   - `_staging/fluencia-b2` — output do ingest ISS **com** `====== FIM DOS METADADOS ======`
3. **E2E** — confirma `E2E: SIM` no terminal (BM25 + queries)

## Ingestão completa (opcional)

Para carregar **todas** as aulas do ISS no MySQL staging:

```bash
./bin/staging-ingest-iss.sh
./bin/staging-serve.sh   # reinicia o bot
```

## Parar

```bash
docker stop kernelbot-mysql-staging
# ou, se tiveres docker compose:
# docker compose -f docker-compose.staging.yml down
```

## Ficheiros

| Ficheiro | Função |
|----------|--------|
| `.env.staging.local` | DB local (3307) |
| `docker-compose.staging.yml` | MySQL Docker |
| `bin/staging-setup.sh` | Setup automático |
| `bin/staging-serve.sh` | Bot + UI com DB staging |
| `scripts/staging/` | Seed e testes E2E |

## Problemas comuns

**`permission denied` no Docker** — adiciona o teu user ao grupo docker e reinicia sessão:
```bash
sudo usermod -aG docker "$USER"
newgrp docker   # ou logout/login
```

**`Table 'kernelbot_staging.knowledge' doesn't exist`** — o container foi criado antes do schema existir. Corrige com:
```bash
./bin/staging-apply-schema.sh
./bin/staging-setup.sh   # ou só: .venv/bin/python scripts/staging/seed_mixed_mass.py
```

**`Connection refused` na porta 3307** — corre `./bin/staging-setup.sh` de novo.

**`OPENROUTER_API_KEY ausente`** — preenche o `.env` principal (só a chave LLM; o DB vem do staging).

**Chat sem resposta / hard stop** — queries de **uma palavra** podem falhar nos gates (`ACL_RETRIEVAL_MIN_TERMS=2`). Usa 2+ termos: ex. `transformers IA generativa`.
