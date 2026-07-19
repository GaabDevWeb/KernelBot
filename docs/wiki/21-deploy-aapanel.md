# Deploy — aaPanel (VPS com painel)

[← Índice](README.md)

Runbook completo para publicar o KernelBot num servidor com **aaPanel** (Linux). Cobre dois caminhos:

- **Caminho A — Python nativo** (recomendado): venv + Uvicorn gerido pelo aaPanel, Nginx como proxy reverso.
- **Caminho B — Docker**: usa o `Dockerfile`/`docker-compose.yml` do repo via gestor Docker do aaPanel.

Variáveis detalhadas: [12-configuracao.md](12-configuracao.md). Deploy Railway/Docker genérico: [20-deploy-railway.md](20-deploy-railway.md).

> **Analogia Laravel:** o fluxo é o mesmo de publicar um app Laravel num VPS — Nginx na frente, um processo de aplicação atrás (aqui Uvicorn no lugar do PHP-FPM), `.env` com credenciais, MySQL do painel e um "seeder" (ingest) para popular a base.

---

## 1. Pré-requisitos

| Item | Detalhe |
|------|---------|
| VPS Linux | Ubuntu 22.04+ / Debian 12 recomendado, mínimo 1 GB RAM (índice BM25 vive em memória) |
| aaPanel instalado | `https://www.aapanel.com/new/download.html` — script oficial de instalação |
| Domínio | Apontado (registo A) para o IP do VPS |
| Python 3.11+ | Instalado via App Store do aaPanel (Python Manager) ou pacote do sistema |
| MySQL 5.7+/8.0 | O do próprio aaPanel serve |
| Chave LLM | **OpenRouter recomendado em servidor** (`ACL_LLM_PROVIDER=openrouter`) — o provider `cursor` exige runtime local do Cursor, raramente adequado em VPS |
| Conteúdo | `jsons/` do repo (aulas espelhadas) e, para o catálogo, `lessons.json` + `search-index.json` do ISS |

Portas: o aaPanel usa 80/443 (Nginx) e a porta do painel (padrão 7800/8888 conforme instalação). A app escuta **8001 apenas em localhost** — não precisa abrir 8001 no firewall.

---

## 2. MySQL — criar base e schema

1. No aaPanel: **Databases → Add database**.
   - Nome: `kernelbot` (ou outro — vai para `DB_NAME`)
   - Utilizador/senha: anote — vão para `DB_USER` / `DB_PASSWORD`
   - Access permission: `localhost` (a app roda no mesmo servidor)
2. Abra o **phpMyAdmin** (ou terminal `mysql`) e crie a tabela `knowledge` na base criada:

```sql
CREATE TABLE IF NOT EXISTS knowledge (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  discipline VARCHAR(128) NOT NULL,
  slug VARCHAR(255) NOT NULL,
  title VARCHAR(512) NOT NULL,
  `order` INT NOT NULL DEFAULT 0,
  content LONGTEXT,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_discipline_slug (discipline, slug),
  KEY idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

> É o mesmo schema de [`docker/init-knowledge.sql`](../../docker/init-knowledge.sql) (lá a base chama-se `kernelbot_staging`; em produção use o nome que criou). Garanta `utf8mb4` — conteúdo das aulas tem acentuação e símbolos.

---

## 3. Caminho A — Python nativo (recomendado)

### 3.1 Obter o código

No terminal do aaPanel (**Terminal** no menu, ou SSH):

```bash
cd /www/wwwroot
git clone https://github.com/GaabDevWeb/KernelBot.git kernelbot
cd kernelbot
```

> `/www/wwwroot` é a raiz de sites do aaPanel (equivalente ao `/var/www` clássico). Usar git facilita atualizações (`git pull`) e rollback (`git checkout <tag>`).

### 3.2 Ambiente virtual e dependências

```bash
cd /www/wwwroot/kernelbot
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-prod.txt
```

Use **`requirements-prod.txt`** (sem pytest/playwright/watchdog — mais leve, igual à imagem Docker).

**Frontend não precisa de build**: o CSS Tailwind compilado (`frontend/assets/css/output.css`) já está versionado no repo. Node.js só é necessário se for alterar estilos.

### 3.3 Configurar `.env`

```bash
cp .env.example .env
nano .env
```

Valores obrigatórios de produção (mesma tabela do [README](../../README.md#deploy-e-produção)):

```bash
# Ambiente
KERNELBOT_ENV=production
KERNELBOT_FORCE_HSTS=true            # atrás do HTTPS do Nginx

# LLM
ACL_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...

# MySQL (criado no passo 2 — localhost, mesmo servidor)
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=kernelbot
DB_USER=kernelbot
DB_PASSWORD=...

# Segurança operacional (obrigatório em produção)
ACL_RELOAD_BEARER_TOKEN=um-token-longo-e-aleatorio   # ex.: openssl rand -hex 32

# Catálogo ISS
ACL_CATALOG_ENABLED=true
ACL_CATALOG_JSON_DIR=/www/wwwroot/kernelbot-content/ISS/content
```

Para o catálogo, copie `lessons.json` e `search-index.json` do ISS para o diretório apontado por `ACL_CATALOG_JSON_DIR` (crie-o se não existir). Sem catálogo, deixe `ACL_CATALOG_ENABLED=false` — `/api/curriculum` responderá 503 e o frontend esconde o mapa curricular (comportamento esperado, sem erro).

### 3.4 Ingestão do conteúdo (popular a tabela)

> **Analogia Laravel:** este passo é o `php artisan db:seed` do projeto — sem ele o chat responde "contexto insuficiente" para tudo.

Com o `.env` já apontando para o MySQL de produção:

```bash
cd /www/wwwroot/kernelbot
./bin/ingest-jsons.sh
# ou diretamente: .venv/bin/python -m engine.jsons_ingest
```

Isso faz UPSERT de `jsons/<disciplina>/*.json` na tabela `knowledge`. Confirme:

```bash
mysql -u kernelbot -p kernelbot -e "SELECT discipline, COUNT(*) FROM knowledge WHERE active=1 GROUP BY discipline;"
```

### 3.5 Teste manual antes de daemonizar

```bash
cd /www/wwwroot/kernelbot
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001
# noutro terminal:
curl -sS http://127.0.0.1:8001/health
```

Se `/health` responder, pare (`Ctrl+C`) e passe ao processo permanente.

**Importante — 1 worker apenas.** Não use `--workers N`: o índice BM25 e o pin de sessão (`PinnedSessionStore`) vivem em memória do processo; múltiplos workers multiplicam RAM e quebram a consistência do pin entre requisições.

### 3.6 Manter o processo vivo (Supervisor do aaPanel)

O aaPanel tem o plugin **Supervisor Manager** (App Store → Supervisor → Install). É o equivalente ao Supervisor que mantém `queue:work` vivo no Laravel.

**App Store → Supervisor Manager → Add Daemon:**

| Campo | Valor |
|-------|-------|
| Name | `kernelbot` |
| Run user | `www` |
| Run dir | `/www/wwwroot/kernelbot` |
| Start command | `/www/wwwroot/kernelbot/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001` |
| Processes | `1` |

Antes de iniciar, dê permissão ao utilizador `www`:

```bash
chown -R www:www /www/wwwroot/kernelbot
```

Alternativa sem plugin — **systemd** (via SSH):

```bash
cat > /etc/systemd/system/kernelbot.service <<'EOF'
[Unit]
Description=KernelBot (FastAPI/Uvicorn)
After=network.target mysql.service

[Service]
User=www
Group=www
WorkingDirectory=/www/wwwroot/kernelbot
ExecStart=/www/wwwroot/kernelbot/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now kernelbot
systemctl status kernelbot
```

> Nota: alguns aaPanel trazem "Python Manager"/"Python Project" na App Store que cria venv + daemon + site numa tela só. Se a sua versão tiver, pode usá-lo no lugar dos passos 3.2/3.6 — aponte o startup para `uvicorn main:app --host 127.0.0.1 --port 8001` e confira que o venv usa Python 3.11+.

### 3.7 Site + proxy reverso no Nginx

1. **Website → Add site**:
   - Domain: `kernelbot.seudominio.com`
   - PHP version: **Pure static** (não é PHP)
2. Entre no site criado → **Reverse Proxy → Add reverse proxy**:
   - Target URL: `http://127.0.0.1:8001`
   - Send domain: `$host`
3. **Edite a config do proxy** (Website → site → Config, ou o ficheiro do proxy em `/www/server/panel/vhost/nginx/proxy/<site>/`). O bloco `location /` precisa de suporte a **SSE** — sem `proxy_buffering off` o streaming do chat chega "de uma vez só" no fim, em vez de token a token:

```nginx
location / {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # SSE (POST /chat com stream) — essencial:
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    proxy_set_header Connection "";
}
```

4. Desative cache do proxy se o template do aaPanel tiver criado bloco de cache (`proxy_cache_valid` etc.) — remove ou comenta.
5. Recarregue o Nginx (o painel faz isso ao salvar).

> O `X-Forwarded-For` importa: o rate limit de `POST /chat` (30 req/min) é por IP; sem o header, todos os utilizadores partilhariam o IP do proxy.

### 3.8 HTTPS (Let's Encrypt)

Website → site → **SSL → Let's Encrypt** → selecionar domínio → Apply. Ative **Force HTTPS**. Com o certificado ativo, mantenha `KERNELBOT_FORCE_HSTS=true` no `.env`.

---

## 4. Caminho B — Docker no aaPanel

Se preferir container (mesma imagem do deploy Railway):

1. App Store → **Docker** (instala Docker + Compose e a UI de gestão).
2. Via terminal:

```bash
cd /www/wwwroot
git clone https://github.com/GaabDevWeb/KernelBot.git kernelbot
cd kernelbot
cp .env.docker.example .env
nano .env      # MySQL + LLM + ACL_RELOAD_BEARER_TOKEN (ver passo 3.3)
docker compose up -d --build
curl -sS http://127.0.0.1:8001/health
```

3. MySQL: o container acessa o MySQL do aaPanel via `DB_HOST=host.docker.internal` (o compose já define `extra_hosts`). No aaPanel, o utilizador MySQL precisa aceitar conexões desse host — em **Databases**, mude a permissão do utilizador de `localhost` para `%` (ou para o IP da bridge Docker, mais restrito).
4. Ingestão: rode o ingest a partir do host (passo 3.4) ou de qualquer máquina com acesso ao MySQL.
5. Proxy reverso + SSL: igual aos passos 3.7 e 3.8 (o alvo continua `http://127.0.0.1:8001`, porta publicada pelo compose — configurável com `KERNELBOT_PUBLISH_PORT`).

---

## 5. Verificação pós-deploy

```bash
# Saúde básica
curl -sS https://kernelbot.seudominio.com/health

# Config pública — deve trazer "catalog_enabled": true (se catálogo ativo)
curl -sS https://kernelbot.seudominio.com/api/public-config

# Catálogo — 200 em produção com ACL_CATALOG_ENABLED=true
curl -sS -o /dev/null -w "%{http_code}\n" https://kernelbot.seudominio.com/api/curriculum

# Drift catálogo ↔ índice (usa o token do .env)
curl -sS -H "Authorization: Bearer SEU_TOKEN" https://kernelbot.seudominio.com/health/catalog
```

Teste de SSE: abra o site, envie uma pergunta no chat e confirme que a resposta chega **progressivamente** (streaming). Se vier tudo de uma vez, revise `proxy_buffering off` (passo 3.7).

Smoke UI opcional a partir da sua máquina local:

```bash
SMOKE_BASE_URL=https://kernelbot.seudominio.com python3 bin/validate-frontend.py
```

---

## 6. Operação

| Ação | Como |
|------|------|
| Ver logs | Supervisor Manager → kernelbot → Log; ou `journalctl -u kernelbot -f` (systemd) |
| Reiniciar app | Supervisor/systemd restart — necessário após editar `.env` |
| Atualizar código | `cd /www/wwwroot/kernelbot && git pull && .venv/bin/pip install -r requirements-prod.txt` → restart |
| Recarregar índice sem restart | `POST /chat` com `{"message": "/reload"}` + header `Authorization: Bearer SEU_TOKEN` (após novo ingest) |
| Novo conteúdo | Atualizar `jsons/` (git pull ou pipeline ISS) → `./bin/ingest-jsons.sh` → `/reload` |
| Logs em JSON | `ACL_LOG_FORMAT=json` no `.env` (uma linha por evento — bom para grep/agregadores) |

### Rollback

1. `cd /www/wwwroot/kernelbot && git log --oneline` → `git checkout <commit-anterior>` (Docker: rebuild da tag anterior).
2. Restart do daemon e conferir `GET /health` + `/api/public-config`.
3. Se o problema for de dados: re-correr ingest + `/reload`.

---

## 7. Troubleshooting

| Sintoma | Causa provável | Correção |
|---------|----------------|----------|
| `502 Bad Gateway` | Uvicorn parado ou porta errada | Ver status no Supervisor/systemd; conferir `127.0.0.1:8001` |
| Boot lento / healthcheck falha no arranque | Índice BM25 constrói no boot (pode levar dezenas de segundos com muitas aulas) | Aumentar `start_period`/tolerância do healthcheck; não é erro |
| Chat responde de uma vez, sem streaming | Buffering do Nginx | `proxy_buffering off` no bloco do proxy (passo 3.7) |
| Todas as respostas: "contexto insuficiente" | Tabela `knowledge` vazia ou `DB_*` errado | Rodar ingest (3.4); conferir credenciais e `SELECT COUNT(*)` |
| `GET /api/curriculum` → 503 | `ACL_CATALOG_ENABLED=false` ou `ACL_CATALOG_JSON_DIR` inválido | Conferir `.env` e existência de `lessons.json`/`search-index.json`; restart |
| `GET /health/catalog` → 503 `reload token not configured` | `ACL_RELOAD_BEARER_TOKEN` vazio | Definir token no `.env`; obrigatório em produção |
| HTTP 429 no `/chat` | Rate limit: 30 req/min por IP (fixo em `api/routes.py`) | Esperado; se todos os IPs parecem um só, conferir `X-Forwarded-For` no Nginx |
| Timeout ao conectar MySQL | `DB_HOST=127.0.0.0` (typo comum) ou permissão do utilizador | Usar `127.0.0.1`; em Docker, permissão `%`/bridge para o utilizador |
| `Permission denied` no arranque | Ficheiros pertencem a root | `chown -R www:www /www/wwwroot/kernelbot` |
| Erro TLS/`cryptography` no MySQL | Faltou dependência | `cryptography` está no `requirements-prod.txt` — reinstalar deps no venv |

---

## Ver também

- [20-deploy-railway.md](20-deploy-railway.md) — Railway, Docker genérico, rollback
- [12-configuracao.md](12-configuracao.md) — todas as variáveis `.env`
- [04-dados-e-mysql.md](04-dados-e-mysql.md) — contrato da tabela `knowledge`
- [10-integracao-iss-fase5b.md](10-integracao-iss-fase5b.md) — pipeline de conteúdo ISS
- [14-seguranca-observabilidade.md](14-seguranca-observabilidade.md) — segurança e logs
