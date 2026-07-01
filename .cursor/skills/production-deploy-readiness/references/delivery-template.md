# Template de entrega — Production Deploy Readiness

Usar **literalmente** estas secções na resposta final.

---

## 1. Arquivos removidos

| Arquivo | Motivo | Evidência |
|---------|--------|-----------|
| … | … | grep / sem uso / artefacto |

## 2. Arquivos modificados

| Arquivo | Alteração | Motivo produção |
|---------|-----------|-----------------|
| … | … | … |

## 3. Configurações revisadas

### Docker

- …

### Ambiente

| Variável | Estado | Acção |
|----------|--------|-------|
| … | … | … |

### Build

- …

### Deploy

- …

### Segurança

- …

### Performance

- …

## 4. Problemas encontrados

| # | Problema | Severidade | Correcção |
|---|----------|------------|-----------|
| 1 | … | alta/média/baixa | … |

## 5. Validação final

| Check | Resultado |
|-------|-----------|
| Projeto inicia | ✅/❌ |
| Frontend | ✅/❌ |
| Backend | ✅/❌ |
| Docker build/config | ✅/❌ |
| Streaming / chat | ✅/❌ |
| ISS / public-config | ✅/❌ |
| Globo / landing | ✅/❌ |
| Modo produção consistente | ✅/❌ |
| Repo limpo (sem artefactos dev) | ✅/❌ |
| pytest | ✅/❌ |
| validate-frontend.py | ✅/❌ |
| Puppeteer 1920×1080 | ✅/❌ |

### Gaps remanescentes (se houver)

- …

### Pronto para deploy imediato?

**Sim / Não** — justificativa em uma frase.
