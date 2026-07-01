# Protocolo de validação — production deploy

Carregar na **Fase 5**. Não declarar readiness sem estes checks.

## 1. Backend unitário

```bash
source .venv/bin/activate
pip install -r requirements.txt -q
PYTHONPATH=. pytest tests/ -q
```

Esperado: todos passam (ou documentar falhas pré-existentes do ambiente).

## 2. Arranque local

```bash
python main.py
```

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/
curl -sS http://127.0.0.1:8001/api/public-config | head -c 300
curl -sS http://127.0.0.1:8001/health
```

## 3. Smoke frontend oficial

```bash
python3 bin/validate-frontend.py
```

Variáveis: `SMOKE_BASE_URL`, `SMOKE_BROWSERS`.

## 4. Modo produção simulado

```bash
KERNELBOT_ENV=production python main.py
```

Verificar:

- [ ] `/src/*` **sem** header `Cache-Control: no-store` forçado pelo middleware dev
- [ ] Headers de segurança presentes

## 5. Docker

```bash
docker build -t kernelbot:ready .
docker compose -f docker-compose.yml config
# docker compose up -d && curl health
```

Documentar se build skip por falta de DB — mínimo: image builds + config válido.

## 6. E2E Puppeteer (obrigatório)

Viewport **1920×1080**.

Checklist:

- [ ] Landing / entrance
- [ ] Globo renderiza (`#globe`)
- [ ] Sidebar + chat input
- [ ] Console sem erros críticos
- [ ] Rede: JS/CSS/assets 200
- [ ] `/api/public-config` OK
- [ ] ISS base URL presente em public-config

## 7. Streaming (amostragem)

Enviar mensagem no chat ou validar via smoke que cobre streaming (`T12`, `T24` em validate-frontend).

## 8. ISS / catálogo

Em **produção simulada** com catálogo enabled:

- `catalog_enabled: true` em public-config
- `GET /api/curriculum` → 200

Em staging local (`ACL_CATALOG_ENABLED=false`): 503 **esperado** — não regressão.

## Falha

Qualquer check crítico falha → corrigir → re-executar suite completa.

Não assinar deploy com regressões conhecidas.
