# Protocolo de auditoria de variáveis de ambiente

Carregar na **Fase 2**.

## Inventário

Listar todos os ficheiros env:

- `.env.example` (SSOT documentado)
- `.env.docker.example`, `.env.railway.example`
- Referências a `.env.production`, `.env.local` na doc — marcar gaps

## Cruzar código ↔ env

```bash
# Variáveis lidas no Python
rg "os\.getenv|os\.environ|Settings" core/ engine/ api/ app/ main.py

# Variáveis ACL_ documentadas
rg "ACL_[A-Z0-9_]+" .env.example core/config.py
```

Para cada variável em `.env.example`:

| Variável | Usada em código? | Obrigatória prod? | Default seguro? | Acção |
|----------|------------------|-------------------|-----------------|-------|

## Categorias

### Mortas

Presentes em `.env.example` mas **zero** leituras no código → remover do example + doc.

### Não documentadas

Lidas no código mas ausentes de `.env.example` → adicionar com comentário.

### Inconsistentes

- Nome diferente entre doc e código
- Default staging em example que contradiz README produção
- Variável "legado" comentada mas ainda lida

### Obrigatórias produção

Validar presença e documentação de:

- `KERNELBOT_ENV`
- `ACL_RELOAD_BEARER_TOKEN`
- `ACL_CATALOG_ENABLED`, `ACL_CATALOG_JSON_DIR`
- `DB_*`
- LLM: `ACL_LLM_PROVIDER` + (`CURSOR_API_KEY` ou `OPENROUTER_API_KEY`)

## Segurança

- [ ] Nenhum segredo real em ficheiros tracked
- [ ] `.env.example` só placeholders vazios
- [ ] Procurar keys expostas: `rg "sk-or-|sk-|api_key=" --glob '!node_modules'`
- [ ] `ACL_RELOAD_BEARER_TOKEN` documentado como obrigatório em prod

## Fallbacks

Verificar `core/config.py` / `Settings.load()`:

- Defaults sensatos quando env ausente
- Falha explícita (raise) para vars críticas em produção vs dev

## Entrega parcial

Incluir tabela resumo no relatório secção **Configurações revisadas → Ambiente**.
