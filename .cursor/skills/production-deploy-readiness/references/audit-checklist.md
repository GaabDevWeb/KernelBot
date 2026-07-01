# Checklist de auditoria — produção

Carregar nas **Fases 3–4**.

## Backend

- [ ] `main.py` boot sem tracebacks
- [ ] `Settings.load()` falha claro sem credenciais
- [ ] Rotas API documentadas respondem (`/`, `/chat`, `/health`, `/api/public-config`, `/api/curriculum`)
- [ ] SSE streaming funcional
- [ ] Rate limit activo em `POST /chat`
- [ ] Sem endpoints debug expostos em produção
- [ ] Logs estruturados sem vazar segredos (`SecretRedactingFilter`)

## Frontend

- [ ] ES modules carregam sem 404
- [ ] CSS compilado presente (`frontend/assets/css/output.css`)
- [ ] Assets referenciados existem (icon, Logo, SVGs sidebar)
- [ ] Sem imports mortos que quebrem runtime
- [ ] Globe, entrance, sidebar, chat composer funcionais

## Segurança

Local: `app/factory.py`

- [ ] `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- [ ] HSTS quando HTTPS / `KERNELBOT_FORCE_HSTS`
- [ ] CSP documentada (limitação `unsafe-inline` conhecida)
- [ ] CORS — verificar se necessário; default restritivo OK para same-origin
- [ ] Bearer token em `/health/catalog` e `/reload`

## Performance

- [ ] Imagens optimizadas; sem assets multi-MB órfãos
- [ ] StaticFiles sem listagem de diretório
- [ ] Em produção: sem `Cache-Control: no-store` forçado em `/src/` (middleware dev off)
- [ ] Compressão — documentar se proxy (nginx) faz gzip; app não precisa se CDN/proxy

## Dependências

```bash
# Python prod vs dev
diff requirements-prod.txt requirements.txt

# Imports não usados (amostragem)
rg "^import |^from " --glob '*.py' api/ app/ core/ engine/
```

- [ ] `requirements-prod.txt` mínimo e suficiente
- [ ] Playwright/pytest **não** em prod
- [ ] `package.json` — deps dev vs runtime Tailwind claras

## Scripts

Inventariar `bin/`, `scripts/` (se existir):

| Script | Runtime? | Dev-only? | Duplicado? | Acção |
|--------|----------|-----------|------------|-------|

Remover scripts mortos com evidência (zero refs + não no README/wiki).

## Documentação

- [ ] README: setup reproduzível do zero
- [ ] Tabela staging vs produção correcta
- [ ] Links internos válidos (`rg "]\(" README.md documentation.md docs/`)
- [ ] Sem referências a ficheiros removidos (QA, TESTE-LOCAL, PROMPT-AGENTE)
- [ ] Deploy Railway/Docker documentado

## Estrutura / artefactos

Remover (com evidência) se presentes:

- `audit-*.png`, `.playwright-mcp/`, `results/`
- Screenshots, logs, coverage, reports
- Pastas vazias após remoções

## Consistência

- [ ] Nomes de disciplinas alinhados (`core/disciplines.json`, frontend)
- [ ] Paths Unix no repo
- [ ] Case-sensitive: imports JS vs filenames

## CI/CD

- [ ] Workflows GitHub existentes e verdes
- [ ] Se ausente: registar no relatório como gap recomendado

## Critério de remoção

> *"Necessário para executar, manter ou evoluir o KernelBot?"*

Se **não** → remover e documentar no relatório.
