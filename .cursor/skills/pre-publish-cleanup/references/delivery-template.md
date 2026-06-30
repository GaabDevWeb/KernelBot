# Template de entrega

Usar **literalmente** estas secções na resposta final ao utilizador.

---

## Arquivos removidos

| Arquivo | Justificativa breve | Evidência |
|---------|---------------------|-----------|
| `path/to/file` | … | grep / sem referências |

## Diretórios removidos

| Diretório | Justificativa breve |
|-----------|---------------------|
| `path/to/dir/` | … |

## Documentação removida

| Documento | Motivo |
|-----------|--------|
| … | plano executado / duplicata / artefacto QA |

## Código morto removido

| Item | Tipo | Evidência |
|------|------|-----------|
| `ModuleX.js` | módulo órfão | zero imports |

## Assets removidos

| Asset | Evidência |
|-------|-----------|
| `audit-foo.png` | não referenciado em HTML/CSS/JS |

## Justificativa

Parágrafo por categoria (artefactos temp, docs obsoletas, código morto, assets órfãos) explicando **por que** a remoção não afecta operação nem distribuição.

## Resultado final

- **Arquivos removidos:** N
- **Diretórios removidos:** N
- **Redução aproximada:** X MB / Y% (comando: `du -sh .` antes/depois, excluindo `.git`, `node_modules`, venvs)
- **Funcionalidade:** ✅ confirmada via pytest + validate-frontend + Puppeteer 1920×1080
- **README actualizado:** sim/não (listar alterações)

## Validação executada

| Check | Resultado |
|-------|-----------|
| pytest | pass/fail |
| python main.py | pass/fail |
| bin/validate-frontend.py | pass/fail |
| Puppeteer E2E | pass/fail |
