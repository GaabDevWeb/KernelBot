# REPORT — Ops Center P2 (Usuários)

Data: 2026-07-29  
Branch: `feature/kernel-ops-center`  
Status: **fechado** (polish + export + 403)

## Entrega

| Ecrã | Rota | Função |
|------|------|--------|
| Sessões | `/ops/users/sessions` | Lista ID/canal/primeiro/último/msgs/status |
| Conversas | `/ops/users/conversations` | Lista + detalhe transcript/pin/traces |
| Estatísticas | `/ops/users/stats` | Msgs, sessões, erros/latência (traces) |
| Bloqueios | `/ops/users/blocks` | Bloquear / desbloquear com motivo |
| Export | `/ops/users/export.zip` | ZIP com JSON+CSV (`user_sessions`, `user_blocks`, `user_stats`) |

## Banco

`ACL_USERS_DB_PATH` (default `data/users.sqlite3`):

- `user_sessions` — touch em cada `/v1/chat` (incrementa msgs em sucesso JSON)
- `user_blocks` — bloqueio activo único por (platform, user_id)

## Hot path

Após auth em `POST /v1/chat`:

1. Se bloqueado → `403` + stage TRACE `ERROR` (`user_blocked`)
2. `touch_session` (first/last seen)
3. Em sucesso JSON → `message_count += 1`

## Gaps fechados neste polish

- Export ZIP (JSON+CSV) para sessões / bloqueios / stats — botões nos 4 ecrãs
- Teste E2E: detalhe de conversa + download export
- Teste: utilizador bloqueado recebe `403` em `POST /v1/chat`
- SQL de stats/traces formatado (sem alterar semântica)

## Limitações (honestas)

- Transcript/pin continuam **in-memory** (reinício limpa a conversa live)
- Sessões/stats/bloqueios são **persistentes** em SQLite
- Erros/latência por user: best-effort via traces (`REQUEST_RECEIVED` + `user_id` no data)
- Export não inclui transcript live nem pins (só SQLite persistente)

## Testes

`PYTHONPATH=. .venv/bin/pytest tests/test_users_ops.py -q`
