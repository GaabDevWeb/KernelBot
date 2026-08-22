"""UI Comunicações — /ops/comms/*."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from api.ops_auth import require_ops_cookie
from api.ops_routes import _ctx
from kernel.comms.security import AttachmentRejected
from kernel.comms.service import (
    build_export_zip,
    execute_campaign,
    operator_jid,
    resolve_preview,
    save_upload,
    send_test,
)
from kernel.comms.store import get_comms_store

router = APIRouter(tags=["comms"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "ops"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _store_or_redirect():
    store = get_comms_store()
    if store is None:
        return None, RedirectResponse(url="/ops/login", status_code=303)
    return store, None


@router.get("/ops/comms", response_class=HTMLResponse)
@router.get("/ops/comms/campaigns", response_class=HTMLResponse)
async def comms_campaigns(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    items = store.list_campaigns(limit=100) if store else []
    flash = request.query_params.get("msg")
    return templates.TemplateResponse(
        request,
        "comms/campaigns.html",
        _ctx("comm-campaigns", items=items, flash=flash, operator=operator_jid()),
    )


@router.get("/ops/comms/campaigns/new", response_class=HTMLResponse)
async def comms_campaign_new(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    templates_list = store.list_templates() if store else []
    audiences = store.list_audiences() if store else []
    return templates.TemplateResponse(
        request,
        "comms/campaign_form.html",
        _ctx(
            "comm-campaigns",
            templates_list=templates_list,
            audiences=audiences,
            error=None,
            preview=None,
            form={},
            operator=operator_jid(),
        ),
    )


@router.post("/ops/comms/campaigns/new", response_class=HTMLResponse)
async def comms_campaign_create(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    channel: str = Form("whatsapp"),
    dest_type: str = Form("user"),
    dest_ref: str = Form(""),
    audience_id: str = Form(""),
    template_id: str = Form(""),
    var_hora: str = Form(""),
    var_link: str = Form(""),
    var_mensagem: str = Form(""),
    scheduled_date: str = Form(""),
    scheduled_time: str = Form(""),
    action: str = Form("save"),
    files: list[UploadFile] = File(default=[]),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)

    variables = {}
    if var_hora.strip():
        variables["hora"] = var_hora.strip()
    if var_link.strip():
        variables["link"] = var_link.strip()
    if var_mensagem.strip():
        variables["mensagem"] = var_mensagem.strip()

    raw_body = body
    if template_id.strip():
        tpl = store.get_template(template_id.strip())
        if tpl and not body.strip():
            raw_body = tpl["body"]
    preview = resolve_preview(raw_body, variables)

    dest_type_n = (dest_type or "user").strip().lower()
    if dest_type_n == "audience":
        dest_ref_n = (audience_id or dest_ref).strip()
    else:
        dest_ref_n = dest_ref.strip()

    form = {
        "title": title,
        "body": raw_body,
        "channel": channel,
        "dest_type": dest_type_n,
        "dest_ref": dest_ref_n,
        "template_id": template_id,
        "var_hora": var_hora,
        "var_link": var_link,
        "var_mensagem": var_mensagem,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
    }

    if action == "preview":
        return templates.TemplateResponse(
            request,
            "comms/campaign_form.html",
            _ctx(
                "comm-campaigns",
                templates_list=store.list_templates(),
                audiences=store.list_audiences(),
                error=None,
                preview=preview,
                form=form,
                operator=operator_jid(),
            ),
        )

    if not title.strip() or not preview.strip():
        return templates.TemplateResponse(
            request,
            "comms/campaign_form.html",
            _ctx(
                "comm-campaigns",
                templates_list=store.list_templates(),
                audiences=store.list_audiences(),
                error="Título e mensagem são obrigatórios.",
                preview=preview,
                form=form,
                operator=operator_jid(),
            ),
            status_code=400,
        )
    if not dest_ref_n:
        return templates.TemplateResponse(
            request,
            "comms/campaign_form.html",
            _ctx(
                "comm-campaigns",
                templates_list=store.list_templates(),
                audiences=store.list_audiences(),
                error="Indique o destino (utilizador, grupo ou público).",
                preview=preview,
                form=form,
                operator=operator_jid(),
            ),
            status_code=400,
        )

    att_ids: list[str] = []
    try:
        for f in files or []:
            if not f or not f.filename:
                continue
            data = await f.read()
            att_ids.append(
                save_upload(store, filename=f.filename, data=data, content_type=f.content_type)
            )
    except AttachmentRejected as exc:
        return templates.TemplateResponse(
            request,
            "comms/campaign_form.html",
            _ctx(
                "comm-campaigns",
                templates_list=store.list_templates(),
                audiences=store.list_audiences(),
                error=str(exc),
                preview=preview,
                form=form,
                operator=operator_jid(),
            ),
            status_code=400,
        )

    scheduled_at = None
    status = "draft"
    if action in {"schedule", "save"} and scheduled_date.strip() and scheduled_time.strip():
        # interpretar como UTC local simplificado (operador deve usar UTC ou offset local consciente)
        try:
            scheduled_at = (
                datetime.fromisoformat(f"{scheduled_date.strip()}T{scheduled_time.strip()}:00")
                .replace(tzinfo=timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%S.000Z")
            )
            if action == "schedule":
                status = "scheduled"
        except ValueError:
            return templates.TemplateResponse(
                request,
                "comms/campaign_form.html",
                _ctx(
                    "comm-campaigns",
                    templates_list=store.list_templates(),
                    audiences=store.list_audiences(),
                    error="Data/hora inválidas.",
                    preview=preview,
                    form=form,
                    operator=operator_jid(),
                ),
                status_code=400,
            )

    cid = store.create_campaign(
        title=title.strip(),
        body=raw_body,
        channel=(channel or "whatsapp").strip().lower(),
        dest_type=dest_type_n,
        dest_ref=dest_ref_n,
        status=status if action != "send_now" else "draft",
        scheduled_at=scheduled_at,
        template_id=template_id.strip() or None,
        preview_text=preview,
        attachment_ids=att_ids,
    )
    store.audit("create_campaign", campaign_id=cid, detail={"action": action, "title": title.strip()})

    if action == "send_test":
        result = await send_test(cid)
        msg = "test_ok" if result.get("ok") else f"test_fail:{result.get('error')}"
        return RedirectResponse(url=f"/ops/comms/campaigns/{cid}?msg={quote(msg)}", status_code=303)

    if action == "send_now":
        result = await execute_campaign(cid)
        msg = "sent_ok" if result.get("ok") else f"sent_fail:{result.get('error')}"
        return RedirectResponse(url=f"/ops/comms/campaigns/{cid}?msg={quote(msg)}", status_code=303)

    if action == "schedule" and status == "scheduled":
        store.audit("schedule_campaign", campaign_id=cid, detail={"scheduled_at": scheduled_at})
        return RedirectResponse(url=f"/ops/comms/campaigns/{cid}?msg=scheduled", status_code=303)

    return RedirectResponse(url=f"/ops/comms/campaigns/{cid}?msg=saved", status_code=303)


@router.get("/ops/comms/campaigns/{campaign_id}", response_class=HTMLResponse)
async def comms_campaign_detail(request: Request, campaign_id: str):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    camp = store.get_campaign(campaign_id)
    if camp is None:
        return RedirectResponse(url="/ops/comms/campaigns?msg=not_found", status_code=303)
    deliveries = store.list_deliveries(campaign_id)
    attachments = store.list_campaign_attachments(campaign_id)
    return templates.TemplateResponse(
        request,
        "comms/campaign_detail.html",
        _ctx(
            "comm-campaigns",
            camp=camp,
            deliveries=deliveries,
            attachments=attachments,
            flash=request.query_params.get("msg"),
            operator=operator_jid(),
        ),
    )


@router.post("/ops/comms/campaigns/{campaign_id}/send-now")
async def comms_send_now(request: Request, campaign_id: str):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    result = await execute_campaign(campaign_id)
    msg = "sent_ok" if result.get("ok") else f"sent_fail:{result.get('error')}"
    return RedirectResponse(url=f"/ops/comms/campaigns/{campaign_id}?msg={quote(msg)}", status_code=303)


@router.post("/ops/comms/campaigns/{campaign_id}/send-test")
async def comms_send_test(request: Request, campaign_id: str):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    result = await send_test(campaign_id)
    msg = "test_ok" if result.get("ok") else f"test_fail:{result.get('error')}"
    return RedirectResponse(url=f"/ops/comms/campaigns/{campaign_id}?msg={quote(msg)}", status_code=303)


@router.post("/ops/comms/campaigns/{campaign_id}/cancel")
async def comms_cancel(request: Request, campaign_id: str):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store:
        store.update_campaign_status(campaign_id, "cancelled")
        store.audit("cancel_campaign", campaign_id=campaign_id)
    return RedirectResponse(url=f"/ops/comms/campaigns/{campaign_id}?msg=cancelled", status_code=303)


@router.get("/ops/comms/schedules", response_class=HTMLResponse)
async def comms_schedules(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    items = store.list_campaigns(status="scheduled", limit=100) if store else []
    return templates.TemplateResponse(
        request, "comms/schedules.html", _ctx("comm-schedules", items=items)
    )


@router.get("/ops/comms/templates", response_class=HTMLResponse)
async def comms_templates(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    items = store.list_templates() if store else []
    return templates.TemplateResponse(
        request, "comms/templates.html", _ctx("comm-templates", items=items, error=None)
    )


@router.post("/ops/comms/templates")
async def comms_templates_create(
    request: Request,
    name: str = Form(...),
    body: str = Form(...),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store:
        tid = store.upsert_template(name=name.strip(), body=body)
        store.audit("create_template", detail={"id": tid, "name": name.strip()})
    return RedirectResponse(url="/ops/comms/templates", status_code=303)


@router.get("/ops/comms/audiences", response_class=HTMLResponse)
async def comms_audiences(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    items = store.list_audiences() if store else []
    return templates.TemplateResponse(
        request, "comms/audiences.html", _ctx("comm-audiences", items=items)
    )


@router.post("/ops/comms/audiences")
async def comms_audience_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store:
        aid = store.create_audience(name=name, description=description)
        store.audit("create_audience", detail={"id": aid, "name": name})
        return RedirectResponse(url=f"/ops/comms/audiences/{aid}", status_code=303)
    return RedirectResponse(url="/ops/comms/audiences", status_code=303)


@router.get("/ops/comms/audiences/{audience_id}", response_class=HTMLResponse)
async def comms_audience_detail(request: Request, audience_id: str):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    aud = store.get_audience(audience_id)
    if not aud:
        return RedirectResponse(url="/ops/comms/audiences", status_code=303)
    members = store.list_audience_members(audience_id)
    return templates.TemplateResponse(
        request,
        "comms/audience_detail.html",
        _ctx("comm-audiences", aud=aud, members=members, error=None),
    )


@router.post("/ops/comms/audiences/{audience_id}/members")
async def comms_audience_add_member(
    request: Request,
    audience_id: str,
    member_type: str = Form("user"),
    member_ref: str = Form(...),
    label: str = Form(""),
):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store:
        store.add_audience_member(
            audience_id,
            member_type=member_type.strip(),
            member_ref=member_ref,
            label=label,
        )
        store.audit("audience_add_member", detail={"audience_id": audience_id, "ref": member_ref})
    return RedirectResponse(url=f"/ops/comms/audiences/{audience_id}", status_code=303)


@router.get("/ops/comms/history", response_class=HTMLResponse)
async def comms_history(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    items = store.list_campaigns(limit=200) if store else []
    return templates.TemplateResponse(
        request, "comms/history.html", _ctx("comm-history", items=items)
    )


@router.get("/ops/comms/export.zip")
async def comms_export(request: Request):
    redirect = require_ops_cookie(request)
    if redirect:
        return redirect
    store = get_comms_store()
    if store is None:
        return RedirectResponse(url="/ops/login", status_code=303)
    data = build_export_zip(store)
    store.audit("export_zip", detail={"bytes": len(data)})
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=comms-export.zip"},
    )
