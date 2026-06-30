# Protocolo de auditoria

Carregar na **Fase 1–2** do workflow.

## Inventário

1. Listar árvore completa (excluir `.git`, `node_modules`, `.venv`, `venv` da análise de remoção — são dependências locais).
2. Para cada ficheiro/diretório na raiz e em `docs/`, `bin/`, `frontend/`, `scripts/`, `results/`, `.playwright-mcp/`, registar classificação.

Use o template mental:

| Path | Categoria | Evidência manter/remover | Referências verificadas |
|------|-----------|--------------------------|-------------------------|

## Verificação de referências (obrigatória)

Antes de classificar como **Remover**, executar buscas:

```bash
# Nome do ficheiro (sem path)
rg -l 'nome-do-ficheiro' --glob '!node_modules' --glob '!.git'

# Imports JS (módulo sem extensão)
rg "from ['\"].*ComponentName" frontend/
rg "import.*ComponentName" frontend/

# Assets (CSS, imagens, fontes)
rg 'url\(|src=|href=' frontend/ templates/
rg 'nome-do-asset' .

# Python
rg 'import |from ' --glob '*.py' .
```

Critério: **zero referências** em runtime, build, deploy, tests ou README principal → candidato a remoção.

Excepções (nunca remover sem prova de obsolescência):

- Entrypoints: `main.py`, `app/factory.py`, `templates/index.html`
- Config deploy: `Dockerfile`, `docker-compose*.yml`, `railway.toml`
- `.env.example`, `requirements*.txt`, `package.json`
- `bin/staging-*.sh`, `bin/validate-frontend.py` (smoke oficial no README)

## Padrões de remoção segura (KernelBot)

| Padrão | Exemplo típico | Acção default |
|--------|----------------|---------------|
| Screenshots de auditoria na raiz | `audit-*.png` | Remover |
| Artefactos MCP/Playwright | `.playwright-mcp/` | Remover diretório |
| Relatórios QA concluídos | `QA_*.md`, `ROADMAP_*.md` | Remover; actualizar README |
| Prompts de agente one-shot | `docs/PROMPT-AGENTE-*.md` | Remover (já no `.gitignore`) |
| Smoke question banks | `PERGUNTAS-SMOKE-*.md` | Remover se não referenciados |
| Resultados de execução | `results/`, `z-respostas.md` | Remover |
| Histórico de agente | `.agent_history.md` | Remover (gitignored) |
| Playground / protótipo | `playground/` | Auditar uso; remover se órfão |

## Código morto

Ordem recomendada:

1. **JS modules** — `rg` por exports não importados em `frontend/src/`
2. **CSS** — selectors só em ficheiros removidos ou nunca referenciados em HTML/JS
3. **Python** — funções/módulos sem callers (`rg` + pytest se existir)

Remover imports mortos no mesmo PR lógico da remoção do módulo.

## Documentação

Manter:

- `README.md` (fonte principal)
- `documentation.md` se referenciado e não duplicar README
- `docs/wiki/` se parte da distribuição
- Guias ainda válidos (ex.: layout canónico se referenciado por contribuidores)

Remover:

- Baselines Lighthouse pós-implementação
- Relatórios de integração já absorvidos no código
- Planos/roadmaps/checklists executados
- Duplicatas entre README e outros `.md`

## Organização pós-limpeza

- Eliminar diretórios vazios
- Consolidar docs dispersos na raiz → `docs/` **só** se agregar valor e não duplicar README
- Garantir `.gitignore` cobre artefactos que voltarão a gerar-se localmente
