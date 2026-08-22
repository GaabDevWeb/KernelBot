"""Exportação ZIP Flight Recorder (v2)."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any

from kernel.trace.store import TraceStore


def build_trace_zip(
    store: TraceStore,
    trace_ids: list[str],
    *,
    scope: str = "selected",
    extra_meta: dict[str, Any] | None = None,
) -> bytes:
    ids = [t for t in dict.fromkeys(trace_ids) if t]
    bundle = store.collect_bundle(ids)

    # Agregar forensics
    conversations: list[dict[str, Any]] = []
    performances: list[dict[str, Any]] = []
    rags: list[dict[str, Any]] = []
    prompts: list[dict[str, Any]] = []
    tokens: list[dict[str, Any]] = []
    systems: list[dict[str, Any]] = []
    single_trace = None

    for tid in ids:
        snap = store.get_snapshot(tid) or {}
        conversations.append({"trace_id": tid, **(snap.get("conversation") or {})})
        performances.append({"trace_id": tid, **(snap.get("performance") or {})})
        rags.append({"trace_id": tid, **(snap.get("rag") or {})})
        prompts.append({"trace_id": tid, **(snap.get("prompt") or {})})
        tokens.append({"trace_id": tid, **(snap.get("tokens") or {})})
        systems.append({"trace_id": tid, **(snap.get("system_metrics") or {})})
        if len(ids) == 1:
            single_trace = {
                "trace": bundle["traces"][0] if bundle["traces"] else {"trace_id": tid},
                "snapshot": snap,
            }

    meta = {
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "scope": scope,
        "trace_count": len(bundle["traces"]),
        "event_count": len(bundle["events"]),
        "trace_ids": ids,
        "format": "flight-recorder-v2",
    }
    if extra_meta:
        meta.update(extra_meta)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # v2 names (spec) + aliases legados
        if single_trace is not None:
            zf.writestr("trace.json", json.dumps(single_trace, ensure_ascii=False, indent=2) + "\n")
        zf.writestr("traces.json", json.dumps(bundle["traces"], ensure_ascii=False, indent=2) + "\n")
        zf.writestr(
            "conversation.json",
            json.dumps(conversations if len(conversations) != 1 else conversations[0], ensure_ascii=False, indent=2)
            + "\n",
        )
        # legado
        zf.writestr(
            "messages.json",
            json.dumps(bundle["messages"], ensure_ascii=False, indent=2) + "\n",
        )
        zf.writestr("events.json", json.dumps(bundle["events"], ensure_ascii=False, indent=2) + "\n")
        zf.writestr(
            "performance.json",
            json.dumps(performances if len(performances) != 1 else performances[0], ensure_ascii=False, indent=2)
            + "\n",
        )
        zf.writestr(
            "rag.json",
            json.dumps(rags if len(rags) != 1 else rags[0], ensure_ascii=False, indent=2) + "\n",
        )
        zf.writestr(
            "prompt.json",
            json.dumps(prompts if len(prompts) != 1 else prompts[0], ensure_ascii=False, indent=2) + "\n",
        )
        zf.writestr(
            "tokens.json",
            json.dumps(tokens if len(tokens) != 1 else tokens[0], ensure_ascii=False, indent=2) + "\n",
        )
        zf.writestr(
            "system_metrics.json",
            json.dumps(systems if len(systems) != 1 else systems[0], ensure_ascii=False, indent=2) + "\n",
        )
        zf.writestr("orbit.log", bundle["orbit_log"] or "")
        zf.writestr("kernel.log", bundle["kernel_log"] or "")
        zf.writestr("metadata.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
        zf.writestr(
            "README.txt",
            (
                "KernelBot Flight Recorder export (v2)\n"
                f"scope={scope}\n"
                f"traces={len(bundle['traces'])}\n"
                "Ficheiros: trace(s).json, conversation.json, events.json, performance.json,\n"
                "rag.json, prompt.json, tokens.json, system_metrics.json, orbit.log, kernel.log, metadata.json\n"
            ),
        )
    return buf.getvalue()
