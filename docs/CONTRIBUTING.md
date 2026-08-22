# Contributing Guide

## Style & Git Workflow

### Código

| Área | Convenção |
|------|-----------|
| Formatação | Python idiomatic; type hints onde já existem |
| Lint | Seguir CI do repo; não introduzir deps UI |
| Naming | pacotes/módulos snake_case; schemas Pydantic claros |
| Testes | `pytest tests/`; preferir testes de API/kernel sem browser |
| Fronteira Kernel | proibido importar HTML/CSS/JS ou servir static de UI |

### Git

**Branches (missão Kernel↔Orbit):**

```bash
# A partir da branch base actual (não resetar histórico)
git checkout -b feature/kernel-orbit-integration
# Se já existir: reutilizar (não recriar)
git checkout feature/kernel-orbit-integration
```

**Branches (missão True Kernel — histórica):**

```bash
git checkout main
git pull
git checkout -b trueKernel
```

Outras features:

```
feature/<descricao-curta>
fix/<descricao>
docs/<descricao>
```

**Nunca** modificar `main` directamente nestas missões. Código da integração Orbit **só** em `feature/kernel-orbit-integration`.

**Commits (Conventional Commits):**

```
feat: descrição curta
fix: descrição
docs: descrição
refactor: descrição
test: descrição
chore: descrição
```

**Pull Requests:**

- [ ] Testes passam localmente (`pytest tests/ -q`)
- [ ] Sem regressão RAG/disciplinas no smoke API
- [ ] PRD/ADR/API_SPEC actualizados se o contrato mudou
- [ ] Sem reintroduzir `frontend/` ou templates UI
- [ ] Descrição com contexto e plano de teste

### Comandos locais

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # credenciais

# Servidor Kernel (API only, pós-refactor)
python main.py         # http://127.0.0.1:8001

# Testes
PYTHONPATH=. pytest tests/ -q

# Health (legado + v1)
curl -sS http://127.0.0.1:8001/health
curl -sS http://127.0.0.1:8001/v1/health
```

Staging MySQL: `./bin/staging-setup.sh` + `./bin/staging-serve.sh` (actualizar scripts se ainda referirem UI).

### Revisão de código

- CI verde obrigatório
- Sem merge directo em `main` sem PR
- Revisar especialmente: contratos `ChatRequest`/`ChatResponse`, remoção de static UI, imports do kernel

## Documentação

- PRD: `docs/prd/`
- ADR: `docs/adr/`
- Specs: `docs/API_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DATA-MODEL.md`
- Wiki histórica: `docs/wiki/` (actualizar ou marcar secções UI como removidas após refactor)

## Contacto / dúvidas

Maintainer do repositório KernelBot / Kernel.
