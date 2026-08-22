# REPORT — Ops Center P4 (Adapters + Configurações)

Data: 2026-07-29  
Branch: `feature/kernel-ops-center`

## Entrega

| Ecrã | Rota | Função |
|------|------|--------|
| WhatsApp | `/ops/adapters/whatsapp` | Status Orbit outbound, sessão, reconexões, msgs hoje/hora (traces) |
| Discord | `/ops/adapters/discord` | Stub `outbound_status` — não activo |
| Modelos | `/ops/settings/models` | Provider, modelo, temperature, timeout (read-only) |
| Prompts | `/ops/settings/prompts` | Lista + mtime + preview + copiar (sem write) |
| Providers | `/ops/settings/providers` | Probe best-effort + latência + último erro |
| Sistema | `/ops/settings/system` | Versão, flags, secrets redigidos, retenção/tracing |

## Ficheiros

- `api/adapters_routes.py`
- `api/settings_routes.py`
- `templates/ops/adapters/{whatsapp,discord}.html`
- `templates/ops/settings/{models,prompts,providers,system}.html`
- `tests/test_adapters_settings_ops.py`
- Wire: `app/factory.py`
- Nav: badges P4 removidos em `api/ops_routes.py`
- Nota: `adapters/README.md`

## Segurança

- Todas as rotas: `require_ops_cookie`
- Secrets/tokens/API keys: nunca renderizados (só `configured`/`missing` ou `***`)
- Status Orbit sanitizado (chaves com token/key/secret/password → `***`; `redact_secrets` em strings)
- Prompts: path traversal bloqueado (`_safe_prompt_path`); sem POST de escrita
- Modelos: sem formulário de edição (não existe padrão env-backed seguro em runtime)

## Gaps (honestos)

1. Msgs hoje/hora no WhatsApp são **globais** (traces Kernel), não filtradas por plataforma.
2. Reconexões só aparecem se Orbit as devolver no JSON de status.
3. Temperature / timeout / lista OpenRouter são **hardcoded** — editar exige `.env` + restart (ou mudança de código).
4. Probe OpenRouter não autentica com a API key (só reachability).
5. Cursor probe = “chave presente”; sem latência de LLM real.

## Testes

`PYTHONPATH=. .venv/bin/pytest tests/test_adapters_settings_ops.py -q`
