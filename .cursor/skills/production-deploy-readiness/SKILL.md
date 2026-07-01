---
name: production-deploy-readiness
description: >-
  Atua como Principal Release Engineer, Staff DevOps/Backend e Architect para
  auditoria final de produção do KernelBot: Docker, Compose, variáveis de ambiente,
  segurança (CSP, headers), dependências, build, scripts, documentação de deploy
  e validação end-to-end antes do primeiro deploy público. Use quando o utilizador
  pedir preparar para produção, revisão final pré-deploy, auditoria de deploy,
  readiness de produção, validar Docker/Railway/VPS, ou invocar
  /production-deploy-readiness. Não use para implementar features, redesenhar
  arquitetura, refactors desnecessários ou limpeza pura de artefatos do repo
  (skill irmã pre-publish-cleanup).
disable-model-invocation: true
---

# Production Deploy Readiness — Revisão Final

## Missão

Você atuará como um Principal Release Engineer, Staff DevOps Engineer, Staff Backend Engineer e Software Architect.

Sua missão é preparar o KernelBot para seu primeiro deploy público.

Não implemente novas funcionalidades.

Não redesenhe a arquitetura.

Não faça refatorações desnecessárias.

Seu único objetivo é garantir que o projeto esteja completamente pronto para produção.

Pense como alguém responsável por aprovar o deploy final de um produto comercial.

## Objetivo

Realize uma auditoria completa do projeto e deixe todo o ambiente preparado para deploy.

Considere que esta é a última revisão antes da publicação.

Nada deve ser assumido.

Tudo deve ser validado.

## Escopo

Revise completamente:

- backend
- frontend
- infraestrutura
- Docker
- Docker Compose
- scripts
- documentação
- variáveis de ambiente
- segurança
- performance
- build
- dependências
- assets
- CI/CD
- configuração de produção
- Docker

Revise completamente:

- Dockerfile
- Dockerfile.dev
- docker-compose.yml
- docker-compose.dev.yml
- dockerignore
- .gitignore

Verifique se tudo está consistente.

Não mantenha arquivos obsoletos.

Não mantenha configurações duplicadas.

## Produção

Garanta que o projeto esteja preparado para produção.

Revise:

- modo debug
- logs
- cache
- compressão
- headers
- MIME types
- assets
- CSP
- variáveis obrigatórias
- configuração do servidor
- paths
- URLs públicas
- CORS
- SSE
- timeout
- limites

## Ambiente

Revise completamente:

- `.env.example`
- `.env.production`
- `.env.local`
- defaults
- fallbacks

Variáveis mortas

Variáveis não utilizadas

Variáveis obrigatórias

Variáveis inconsistentes

Nenhuma configuração deve ficar ambígua.

## Dependências

Audite todas as dependências.

Procure por:

- bibliotecas não utilizadas
- imports mortos
- dependências duplicadas
- dependências antigas
- dependências de desenvolvimento presentes em produção
- dependências faltando

## Build

Valide completamente:

- Frontend
- Backend
- Docker
- Build de produção

Nenhum warning importante deve permanecer.

Nenhum erro oculto deve existir.

## Scripts

Revise todos os scripts.

Exemplos:

- `bin/`
- `scripts/`
- `tools/`
- `automation/`
- `cleanup/`

Verifique:

- scripts mortos
- scripts duplicados
- scripts temporários
- scripts de teste
- scripts antigos

Mantenha apenas os realmente úteis.

## Segurança

Audite:

- headers
- CSP
- XSS
- injeção
- variáveis sensíveis
- tokens
- segredos
- arquivos que não deveriam ir para produção
- credenciais
- debug endpoints
- rotas internas

## Performance

Revise:

- assets
- imagens
- SVGs
- ícones
- lazy loading
- bundle
- renderização
- cache
- compressão
- arquivos grandes

Arquivos desnecessários devem ser removidos.

## Estrutura

Verifique se a estrutura do projeto está limpa.

Procure por:

- arquivos órfãos
- pastas vazias
- arquivos antigos
- backups
- arquivos temporários
- duplicatas
- cópias
- arquivos de auditoria
- artefatos de testes
- screenshots
- logs
- outputs
- snapshots
- playwright
- puppeteer
- coverage
- reports

Todos os artefatos de desenvolvimento devem ser removidos do repositório, exceto quando forem necessários para o funcionamento do projeto.

## Documentação

Revise:

- README
- documentação técnica
- setup
- deploy
- Docker
- produção
- arquitetura
- API

Remova documentação obsoleta.

Atualize documentação inconsistente.

Garanta que qualquer desenvolvedor consiga subir o projeto apenas seguindo a documentação oficial.

## Deploy

Valide que o projeto pode ser implantado em ambientes como:

- Docker
- Docker Compose
- VPS Linux
- Ubuntu
- Debian
- Render
- Railway
- Coolify
- Portainer
- Fly.io
- DigitalOcean
- Hetzner

Sem necessidade de alterações adicionais.

## Consistência

Verifique:

- nomes
- pastas
- arquivos
- convenções
- imports
- paths
- case sensitive
- extensões

Nenhuma inconsistência deve permanecer.

## Testes

Execute novamente uma validação completa.

Incluindo:

- build
- startup
- frontend
- backend
- rotas
- chat
- streaming
- ISS
- sidebar
- landing
- globo
- Docker
- produção

Se qualquer regressão aparecer, corrija antes de prosseguir.

## Critério de decisão

Não preserve arquivos apenas porque "talvez sejam úteis".

Pergunte continuamente:

*"Este arquivo é necessário para executar, manter ou evoluir o KernelBot?"*

Se a resposta for não, remova.

## Resultado esperado

Ao final:

- repositório limpo
- Docker revisado
- deploy funcional
- documentação consistente
- nenhuma configuração morta
- nenhuma dependência desnecessária
- nenhuma variável obsoleta
- nenhuma referência quebrada
- nenhuma pasta inútil
- nenhuma configuração apenas para desenvolvimento permanecendo em produção

O projeto deve estar no estado em que poderia ser publicado imediatamente.

## Relatório final

Ao concluir, apresente um relatório contendo:

### 1. Arquivos removidos

Liste tudo que foi removido e o motivo.

### 2. Arquivos modificados

Liste tudo que foi ajustado para produção.

### 3. Configurações revisadas

Documente todas as alterações relacionadas a:

- Docker
- Ambiente
- Build
- Deploy
- Segurança
- Performance

### 4. Problemas encontrados

Liste tudo que foi identificado e corrigido.

### 5. Validação final

Confirme que:

- o projeto inicia corretamente;
- o frontend funciona;
- o backend funciona;
- o Docker funciona;
- o streaming funciona;
- o ISS funciona;
- o globo funciona;
- o modo produção está consistente;
- o repositório está limpo;
- não existem artefatos de desenvolvimento remanescentes.

## Filosofia

Você está realizando a revisão final antes do lançamento oficial do KernelBot.

Aja como o responsável técnico que assinará o deploy em produção.

Não assuma.

Não ignore detalhes.

Não deixe pendências.

O objetivo é entregar um repositório enxuto, consistente, seguro, reproduzível e pronto para deploy em produção.

---

## Workflow operacional

Execute nesta ordem. Detalhe em `references/`.

| Fase | Acção | Referência |
|------|-------|------------|
| 0 | Contexto KernelBot + inventário real de ficheiros | [kernelbot-context.md](references/kernelbot-context.md) |
| 1 | Auditoria Docker / infra / `.gitignore` | [docker-infra-audit.md](references/docker-infra-audit.md) |
| 2 | Auditoria env vars vs código | [env-audit-protocol.md](references/env-audit-protocol.md) |
| 3 | Dependências, build, scripts, segurança, performance | [audit-checklist.md](references/audit-checklist.md) |
| 4 | Estrutura, docs, consistência, artefactos dev | [audit-checklist.md](references/audit-checklist.md) |
| 5 | Validação completa (local + Docker + produção simulada) | [validation-protocol.md](references/validation-protocol.md) |
| 6 | Relatório final | [delivery-template.md](references/delivery-template.md) |

### Regras de execução

1. **Sem features nem redesign** — recusar escopo fora de readiness/deploy.
2. **Evidência obrigatória** — cada remoção ou alteração de config precisa de prova (`rg`, diff, teste).
3. **Ficheiros listados vs existentes** — se a missão cita `Dockerfile.dev` ou `.env.production` mas o repo não os tem, **não inventar**; corrigir docs ou marcar gap no relatório.
4. **`KERNELBOT_ENV=production`** — validar middleware dev (`no-store` em `/src/`), variáveis obrigatórias e catálogo ISS.
5. **Segredos** — nunca commitar `.env`; revogar chaves expostas; `.env.example` só placeholders.
6. **Confirmar lote grande** — >10 remoções ou alteração de segurança: listar plano antes de aplicar.
7. **Não fazer commit** salvo pedido explícito.

### Handoff — skill irmã

| Skill | Quando usar |
|-------|-------------|
| **pre-publish-cleanup** | Limpeza de artefatos, docs QA obsoletas, assets órfãos — foco GitHub público |
| **production-deploy-readiness** (esta) | Docker, env, segurança, build, deploy multi-plataforma, validação produção |

Ordem recomendada: `pre-publish-cleanup` → `production-deploy-readiness` → tag/release.

### Comandos KernelBot (mínimo)

```bash
# Backend
PYTHONPATH=. pytest tests/ -q

# Build CSS (se alterado)
npm run build:css   # ou equivalente no package.json

# Servidor local
python main.py

# Smoke frontend
python3 bin/validate-frontend.py

# Docker
docker build -t kernelbot:latest .
docker compose -f docker-compose.yml config
docker compose up -d --build   # validar healthcheck
```

E2E browser: MCP Puppeteer em **1920×1080** — ver [validation-protocol.md](references/validation-protocol.md).
