"""Scheduler simples de campanhas agendadas (asyncio — sem Redis/Rabbit)."""

from __future__ import annotations

import asyncio
import logging

from kernel.comms.service import execute_campaign
from kernel.comms.store import get_comms_store

log = logging.getLogger("kernelbots.comms.scheduler")

_task: asyncio.Task | None = None
_stopping = False


async def _loop(interval_s: float = 20.0) -> None:
    global _stopping
    while not _stopping:
        try:
            store = get_comms_store()
            if store is not None:
                due = store.due_scheduled()
                for camp in due:
                    log.info("Executando campanha agendada %s", camp.id)
                    store.audit("scheduled_fire", campaign_id=camp.id)
                    try:
                        await execute_campaign(camp.id)
                    except Exception as exc:
                        log.warning("Falha agendamento %s: %s", camp.id, exc)
        except Exception as exc:
            log.warning("comms scheduler tick: %s", exc)
        await asyncio.sleep(interval_s)


async def start_comms_scheduler() -> None:
    global _task, _stopping
    _stopping = False
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="comms-scheduler")
    log.info("Comms scheduler iniciado")


async def stop_comms_scheduler() -> None:
    global _task, _stopping
    _stopping = True
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
