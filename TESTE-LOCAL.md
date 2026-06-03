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

## Checklist grounding `anchored` (default)

Com `ACL_GROUNDING_POLICY=anchored` no `.env` (ou omitido — default em código):

1. **On-corpus** (`reason=ok`): pergunta da tabela acima → resposta cita `[Fonte: …]` e pode incluir bloco *Extensão pedagógica (fora do material indexado):* **sem** override `post_generation_misalignment` no fim.
2. **Off-corpus** (pergunta fora do índice, 2+ termos): aviso de lacuna ou nota permissiva — **sem** inventar comandos do ACL.
3. **A/B:** repetir a mesma pergunta com `ACL_GROUNDING_POLICY=strict` → resposta mais conservadora (sem extensão pedagógica rotulada).
4. **Desambiguação:** com `ACL_DISAMBIGUATION_ENABLED=true`, comportamento de chips inalterado.

`pytest tests/test_context_grounding.py tests/test_post_generation_anchored.py -q`

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

## Smoke test de latência (browser)

Requer `staging-serve` activo e DevTools (F12).

1. **Rede lenta:** DevTools → Network → Throttling → **Slow 3G** (ou Fast 3G).
2. **Desambiguação com geração:** no `.env` usado pelo staging, `ACL_DISAMBIGUATION_ENABLED=true`. Reinicia `./bin/staging-serve.sh`.
3. Envia pergunta ambígua (2+ hits no índice mínimo), ex.: `níveis integridade relacional transformers`.
4. **Balão vazio (regressão):** durante o stream só com `<ambiguity_options>`, o balão deve mostrar o placeholder *«A preparar opções de escolha…»* (barra lateral azul), **não** ficar em branco até ao fim.
5. **Verificar durante o stream:**
   - Não aparece texto cru `<ambiguity_options>` na bolha.
   - Se o modelo/camada emitir opções, surgem **chips** (`.disambiguation-chips`) como no hard stop.
   - Breadcrumb: hint cinza “Várias fontes próximas…”.
6. **Hard-cut (Offline):** DevTools → **Offline** a meio do XML — abort imediato; mensagem de interrupção ou chips parciais válidos.
6b. **Rede pendurada (Slow 3G):** deixa o stream parar de enviar bytes **sem** Offline; após **~15s** (`DEFAULT_STREAM_INACTIVITY_MS` em `api.js`) deve aparecer aviso de inatividade — **não** placeholder infinito.
6c. **Texto antes do XML:** intro em `.stream-prose`, placeholder em `.stream-ambiguity-slot` (sem apagar o parágrafo).
6d. **Texto depois do XML:** frase após `</ambiguity_options>` deve aparecer em **`.stream-post-ambiguity`**, **abaixo** dos chips (ordem: intro → chips → pós-texto).
6e. **Chips incrementais:** cada `<option …/>` completa deve aparecer no slot **sem** esperar o fim do stream; opções incompletas ficam ocultas.
6f. **CLS:** ao fechar `</ambiguity_options>`, o placeholder some **antes** do texto em `.stream-post-ambiguity`; o texto inferior não deve saltar quando os chips terminam de montar.
6g. **Timeout no meio do XML:** com 2+ `<option/>` já recebidas e rede pendurada ~15s → chips visíveis + nota “opções recuperadas”, **não** placeholder eterno.
7. **Verificar meta tardio (opcional):** na aba Network, resposta `POST /chat` → eventos `data: [ACL_META]` — pode haver meta com `disambiguation_options` ou override `post_generation_override`.
8. **Override pós-geração:** se o sanity check disparar, o hint passa a **amarelo** (misalignment) e o header mostra **Revisão** — chips removidos/invalidados.
9. **Abort / falha:** interromper o carregamento da página ou fechar o separador a meio do stream → badge do header volta a **Online**; `finalizeAmbiguityStreamDisplay` não deixa bolha zumbi vazia.
