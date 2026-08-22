# REPORT — Comunicações (Kernel Ops)

Data: 2026-07-29  
Modo frontend-pro: **Build** (Jinja ops shell)

## 1. Arquitetura

```text
Painel /ops/comms/*
        ↓
kernel/comms (store SQLite + scheduler asyncio + service)
        ↓
adapters/whatsapp/outbound.py  (HTTP interno)
        ↓
Orbit :8010 POST /internal/outbound/send
        ↓
Baileys sendMessage (texto / imagem / doc / vídeo / áudio)
```

Discord: stub em `adapters/discord/outbound.py`.

## 2. Schema SQLite (`ACL_COMM_DB_PATH`, default `data/comms.sqlite3`)

| Tabela | Função |
|--------|--------|
| `comm_campaigns` | Campanhas / agendamentos |
| `comm_templates` | Templates com `{vars}` |
| `comm_audiences` + `comm_audience_members` | Públicos |
| `comm_attachments` | Dedup por sha256 |
| `comm_campaign_attachments` | N:N |
| `comm_deliveries` | Resultado por destino |
| `comm_audit` | Auditoria local |

Anexos em disco: `ACL_COMM_ATTACHMENTS_DIR` (dedup por hash).

## 3. Rotas

| Rota | Função |
|------|--------|
| `/ops/comms/campaigns` | Lista |
| `/ops/comms/campaigns/new` | Criar + preview + send test/now/schedule |
| `/ops/comms/campaigns/{id}` | Detalhe + entregas |
| `/ops/comms/schedules` | Agendados |
| `/ops/comms/templates` | CRUD simples |
| `/ops/comms/audiences` | Públicos |
| `/ops/comms/history` | Histórico |
| `/ops/comms/export.zip` | JSON+CSV |

Orbit: `GET /internal/health`, `GET /internal/outbound/status`, `POST /internal/outbound/send`.

## 4. Telas

Campanhas, formulário (pré-visualização + Enviar Teste obrigatório no fluxo), detalhe, agendamentos, templates, públicos, histórico — no shell Ops existente.

## 5–7. Fluxos

- **Envio:** criar → (preview) → Enviar Teste (`ACL_COMM_OPERATOR_JID`) → Enviar Agora → deliveries + audit + stages TRACE `COMM_SEND_*`
- **Agendamento:** status `scheduled` + `scheduled_at` UTC → scheduler ~20s → `execute_campaign`
- **Auditoria:** `comm_audit` + `emit_kernel(COMM_SEND_*)`

## 8. Integração adapters

Cliente Kernel: `adapters/whatsapp/outbound.py` → `ORBIT_INTERNAL_URL`.  
Sem Baileys no processo Python.

## 9. Segurança

- Upload allowlist: png/jpg/webp/pdf/docx/mp4/mp3/zip (+ogg/webm)
- Bloqueio exe/js/html/sh/…
- Max 8 MiB; sem HTML activo nos templates
- Auth cookie ops + Bearer interno Orbit
- Bind Orbit `127.0.0.1` por default

## 10. Critérios de sucesso

| # | Critério | Estado |
|---|----------|--------|
| 1 | Criar campanha | Sim |
| 2 | Anexar ficheiro | Sim |
| 3 | Agendar | Sim |
| 4 | Enviar teste | Sim (requer JID + Orbit up) |
| 5 | Enviar grupo/público | Sim |
| 6 | Histórico | Sim |
| 7 | Auditar | Sim |
| 8 | Exportar | ZIP JSON+CSV |
| 9 | Operar no painel | Sim |
| 10 | Adapter WhatsApp | Sim (novo outbound Orbit) |

## Configuração

```bash
# Kernel
ACL_COMM_OPERATOR_JID=5511...
ORBIT_INTERNAL_URL=http://127.0.0.1:8010
ACL_INTERNAL_BEARER_TOKEN=...

# Orbit (mesmo token)
ACL_INTERNAL_BEARER_TOKEN=...
ORBIT_INTERNAL_PORT=8010
```

## Testes

`PYTHONPATH=. .venv/bin/pytest tests/test_comms.py -q`  
Orbit: `npm test` (normalize JID).
