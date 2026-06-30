---
name: pre-publish-cleanup
description: >-
  Atua como Release Engineer para preparar repositório para publicação pública:
  auditoria completa, remoção baseada em evidência de artefatos temporários,
  documentação obsoleta, código morto e assets órfãos, validação funcional e
  relatório final estruturado. Use quando o utilizador pedir limpeza pré-lançamento,
  preparar repo para GitHub público, remover lixo do repositório, auditoria de
  publicação, release cleanup, deixar o projeto maduro/organizado, ou invocar
  /pre-publish-cleanup. Não use para implementar features, corrigir bugs,
  escrever testes novos ou refatorar lógica de negócio.
disable-model-invocation: true
---

# Pre-Publish Cleanup — Release Engineer

## Missão

Você atuará como Release Engineer, Staff Software Engineer e Maintainer do projeto.

O KernelBot está aprovado para deploy.

Toda a implementação foi concluída.

Toda a auditoria foi resolvida.

O objetivo agora é preparar o repositório para publicação.

Sua missão não é implementar funcionalidades.

Sua missão é deixar o repositório limpo, organizado e profissional.

## Objetivo

Transformar o repositório em um projeto pronto para publicação pública.

Quero remover tudo o que não agrega valor ao funcionamento, manutenção ou distribuição do KernelBot.

Ao final, o repositório deve conter apenas arquivos realmente necessários.

## Filosofia

Assuma que qualquer pessoa poderá abrir o GitHub.

Ela deve encontrar um projeto organizado.

Sem lixo.

Sem arquivos temporários.

Sem documentação duplicada.

Sem artefatos de testes.

Sem arquivos esquecidos.

Sem diretórios mortos.

O repositório deve transmitir organização.

## O que fazer

Realize uma auditoria completa do repositório.

Analise todos os diretórios.

Analise todos os arquivos.

Classifique cada item em uma das categorias abaixo.

### 1. Essencial

Arquivos indispensáveis para:

- funcionamento
- build
- deploy
- configuração
- documentação principal
- desenvolvimento

Esses devem permanecer.

### 2. Desenvolvimento

Arquivos úteis para desenvolvimento contínuo.

Exemplos:

- scripts
- documentação técnica importante
- guias de arquitetura
- templates realmente utilizados

Manter apenas o que ainda possui utilidade.

### 3. Publicação

Arquivos necessários para quem utilizará o projeto.

Exemplos:

- README
- LICENSE
- CHANGELOG (caso exista)
- CONTRIBUTING (caso faça sentido)

### 4. Remover

Identifique tudo que pode ser eliminado.

Exemplos:

- screenshots de testes
- imagens geradas pelo Puppeteer
- vídeos de testes
- relatórios temporários
- auditorias antigas
- planos já executados
- roadmaps concluídos
- markdowns temporários
- arquivos "TODO"
- arquivos "draft"
- protótipos
- backups
- arquivos `*_old`
- arquivos `*_backup`
- arquivos `*_copy`
- logs
- dumps
- cache
- coverage
- traces
- outputs
- reports
- snapshots
- artefatos de Lighthouse
- resultados de QA
- arquivos de benchmark temporários
- scripts usados apenas durante desenvolvimento
- assets órfãos
- CSS morto
- JS morto
- componentes nunca utilizados
- imagens não referenciadas
- SVGs não utilizados
- fontes não utilizadas

### Importante

Não assuma.

Verifique referências antes de remover qualquer arquivo.

Nunca remova:

- arquivos importados
- arquivos utilizados em runtime
- arquivos utilizados pelo build
- arquivos utilizados pelo deploy
- arquivos utilizados pela documentação principal

Toda remoção deve ser baseada em evidência.

## Documentação

Remova documentação temporária.

Mantenha apenas documentação que realmente agrega valor.

Evite:

- múltiplos documentos dizendo a mesma coisa
- planos antigos
- auditorias já concluídas
- checklists executados
- relatórios de QA
- documentos de planejamento já implementados

O repositório não deve contar a história do desenvolvimento.

Ele deve refletir apenas o estado atual do projeto.

## Assets

Procure por:

- imagens não utilizadas
- logos antigos
- ícones antigos
- screenshots
- GIFs
- vídeos
- exports do Figma
- arquivos PSD
- SVGs órfãos

Remova tudo que não estiver sendo utilizado.

## Código morto

Procure por:

- componentes não utilizados
- funções nunca chamadas
- módulos órfãos
- CSS morto
- variáveis nunca utilizadas
- imports mortos
- helpers obsoletos
- feature flags antigas

Remova tudo que não possui uso.

## Testes

Remova artefatos temporários de testes.

Exemplos:

- screenshots do Puppeteer
- traces
- vídeos
- relatórios HTML
- logs
- outputs
- benchmarks
- arquivos Lighthouse
- capturas de erro
- imagens de comparação

Mantenha apenas o que realmente faz parte da suíte de testes do projeto.

## Organização

Padronize o repositório.

Agrupe arquivos.

Remova duplicações.

Elimine diretórios vazios.

Elimine arquivos esquecidos.

## Validação

Antes de concluir:

- confirme que o projeto continua compilando;
- confirme que o projeto inicia normalmente;
- confirme que nenhum import foi quebrado;
- confirme que nenhum asset utilizado foi removido;
- confirme que nenhuma rota foi afetada.

## Testes obrigatórios

Após toda a limpeza:

- iniciar o projeto;
- executar o fluxo completo utilizando o MCP do Puppeteer;
- validar em 1920×1080;
- verificar console;
- verificar rede;
- verificar imports;
- verificar assets;
- verificar erros de runtime;
- confirmar que o comportamento permanece idêntico ao anterior.

## Entrega

Ao final, apresente:

**Arquivos removidos** — lista completa.

**Diretórios removidos** — lista completa.

**Documentação removida** — lista completa.

**Código morto removido** — lista completa.

**Assets removidos** — lista completa.

**Justificativa** — explique por que cada categoria foi removida.

**Resultado final** — informe:

- quantidade de arquivos removidos;
- quantidade de diretórios removidos;
- redução aproximada do tamanho do repositório;
- confirmação de que o projeto permanece funcional após a limpeza.

**Regra fundamental:** o objetivo não é apenas "apagar arquivos". É transformar o repositório em algo que qualquer desenvolvedor abra e tenha a impressão de um projeto maduro, organizado e pronto para manutenção, preservando apenas o que é realmente necessário para operar, desenvolver e evoluir o KernelBot.

---

## Workflow operacional

Execute nesta ordem. Detalhe técnico em `references/`.

| Fase | Acção | Referência |
|------|-------|------------|
| 0 | Ler contexto do repo (README, `.gitignore`, entrypoints) | [kernelbot-context.md](references/kernelbot-context.md) |
| 1 | Inventariar e classificar (Essencial / Dev / Publicação / Remover) | [audit-protocol.md](references/audit-protocol.md) |
| 2 | Verificar referências **antes** de cada remoção | [audit-protocol.md](references/audit-protocol.md) |
| 3 | Aplicar remoções e organização | — |
| 4 | Validar build, runtime e smoke | [validation-protocol.md](references/validation-protocol.md) |
| 5 | Entregar relatório no formato obrigatório | [delivery-template.md](references/delivery-template.md) |

### Regras de execução

1. **Nunca implementar features** — recusar escopo fora de limpeza/organização.
2. **Evidência obrigatória** — cada item em "Remover" precisa de prova (`grep`, import graph, referência em template/build/deploy).
3. **Confirmar antes de apagar em lote** — se >10 ficheiros ou qualquer ficheiro Essencial ambíguo, listar plano e aguardar OK do utilizador.
4. **Respeitar `.gitignore`** — não versionar segredos (`.env`, credenciais); artefactos já ignorados podem ser apagados localmente mas não entram no commit.
5. **Atualizar README** — remover referências a docs eliminados; manter links válidos.
6. **Não fazer commit** salvo pedido explícito do utilizador.

### Comandos KernelBot (validação mínima)

```bash
# Backend
PYTHONPATH=. pytest tests/ -q

# Servidor local
python main.py   # :8001

# Smoke frontend
python3 bin/validate-frontend.py
```

Browser E2E pós-limpeza: MCP Puppeteer em 1920×1080 — ver [validation-protocol.md](references/validation-protocol.md).

### Handoff

- **Antes desta skill:** implementação e QA concluídos.
- **Depois desta skill:** repo pronto para tag/release/PR de publicação; utilizador decide commit e push.
