# Protocolo de validação pós-limpeza

Carregar na **Fase 4**. Não declarar conclusão sem passar nestes checks.

## 1. Backend

```bash
cd /path/to/KernelBot
source .venv/bin/activate   # ou venv existente
pip install -r requirements.txt -q
PYTHONPATH=. pytest tests/ -q
```

Esperado: testes passam (ou mesma baseline pré-limpeza se ambiente incompleto — documentar).

## 2. Arranque

```bash
python main.py
```

Verificar:

- `GET /` → 200
- `GET /api/public-config` → JSON válido
- Sem tracebacks no terminal

Parar servidor antes do smoke browser.

## 3. Smoke oficial

```bash
python3 bin/validate-frontend.py
```

Variáveis: `SMOKE_BASE_URL` (default `http://127.0.0.1:8001`).

## 4. E2E via MCP Puppeteer (obrigatório na skill)

Viewport: **1920×1080**.

Checklist:

- [ ] Página inicial / entrance carrega
- [ ] Console sem erros críticos (warnings conhecidos documentados OK)
- [ ] Rede: assets 200 (`/src/`, `/assets/`, API)
- [ ] Chat input visível após entrance
- [ ] Nenhum 404 em JS/CSS referenciados
- [ ] Comportamento visual equivalente ao pré-limpeza

Preferir MCP `user-puppeteer` ou `user-playwright` conforme disponível no ambiente.

## 5. Imports e assets

Após remoções de código/assets:

```bash
# Quebrar imports JS
rg "from '\./" frontend/src --glob '*.js' | head   # amostragem manual

# Assets órfãos inversos — ficheiro referenciado mas ausente
rg -o "/assets/[^\"']+" frontend templates | sort -u
# confirmar cada path existe no disco
```

## 6. Regressão de rotas API

Smoke mínimo:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/
curl -sS http://127.0.0.1:8001/api/public-config | head -c 200
```

Em staging local, `GET /api/curriculum` → 503 é **esperado** (`ACL_CATALOG_ENABLED=false`).

## Falha

Se qualquer check falhar:

1. Reverter remoção suspeita ou corrigir referência quebrada
2. Re-executar validação completa
3. Não entregar relatório final como sucesso
