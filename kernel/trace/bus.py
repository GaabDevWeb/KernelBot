"""Fila async best-effort para escrita de TRACE (ERROR prioritário)."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from kernel.trace.stages import PRIORITY_ERROR, PRIORITY_NORMAL
from kernel.trace.store import TraceStore

log = logging.getLogger("kernelbots.trace.bus")

_SEQ = 0


def _next_seq() -> int:
    global _SEQ
    _SEQ += 1
    return _SEQ


@dataclass(order=True)
class _QueuedEvent:
    priority: int
    seq: int
    trace_id: str = field(compare=False)
    timestamp: str | None = field(compare=False, default=None)
    service: str = field(compare=False, default="")
    stage: str = field(compare=False, default="")
    data: dict[str, Any] = field(compare=False, default_factory=dict)


class TraceBus:
    """`emit` nunca propaga excepção ao caller (best-effort)."""

    def __init__(
        self,
        store: TraceStore,
        *,
        maxsize: int = 5000,
        retention_days: int | None = None,
        retention_interval_s: float = 3600.0,
    ) -> None:
        self.store = store
        self._queue: asyncio.PriorityQueue[_QueuedEvent] = asyncio.PriorityQueue(maxsize=maxsize)
        self._worker: asyncio.Task | None = None
        self._retention_task: asyncio.Task | None = None
        self._stopping = False
        if retention_days is None:
            try:
                retention_days = int((os.getenv("ACL_TRACE_RETENTION_DAYS") or "30").strip())
            except ValueError:
                retention_days = 30
        self.retention_days = max(1, int(retention_days))
        self.retention_interval_s = max(60.0, float(retention_interval_s))

    def queue_size(self) -> int:
        try:
            return int(self._queue.qsize())
        except Exception:
            return 0

    async def start(self) -> None:
        if self._worker is not None and not self._worker.done():
            return
        self._stopping = False
        self._worker = asyncio.create_task(self._run(), name="trace-bus-worker")
        self._retention_task = asyncio.create_task(
            self._retention_loop(), name="trace-retention"
        )

    async def stop(self) -> None:
        self._stopping = True
        try:
            self._queue.put_nowait(
                _QueuedEvent(priority=99, seq=_next_seq(), trace_id="", stage="__stop__")
            )
        except asyncio.QueueFull:
            pass
        if self._retention_task is not None:
            self._retention_task.cancel()
            try:
                await self._retention_task
            except (asyncio.CancelledError, Exception):
                pass
            self._retention_task = None
        if self._worker is not None:
            try:
                await asyncio.wait_for(self._worker, timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                self._worker.cancel()
            self._worker = None

    def emit(
        self,
        *,
        trace_id: str,
        service: str,
        stage: str,
        data: dict[str, Any] | None = None,
        timestamp: str | None = None,
        priority: int | None = None,
    ) -> bool:
        """Enfileira evento. Retorna False se fila cheia / não iniciado."""
        try:
            stg = (stage or "").strip()
            prio = PRIORITY_ERROR if stg.upper() == "ERROR" else (
                PRIORITY_NORMAL if priority is None else int(priority)
            )
            item = _QueuedEvent(
                priority=prio,
                seq=_next_seq(),
                trace_id=(trace_id or "").strip(),
                timestamp=timestamp,
                service=(service or "").strip(),
                stage=stg,
                data=dict(data or {}),
            )
            if not item.trace_id or not item.stage or item.stage == "__stop__":
                return False
            self._queue.put_nowait(item)
            return True
        except Exception as exc:
            log.warning("trace emit dropped: %s", exc)
            return False

    async def flush(self, timeout: float = 2.0) -> None:
        """Espera a fila esvaziar (testes)."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while not self._queue.empty():
            if loop.time() >= deadline:
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.05)

    async def _retention_loop(self) -> None:
        while not self._stopping:
            try:
                await asyncio.sleep(self.retention_interval_s)
                if self._stopping:
                    break
                purged = await asyncio.to_thread(
                    self.store.purge_older_than, self.retention_days
                )
                if purged:
                    log.info(
                        "Trace retention periódica: removidos %s traces (> %s dias)",
                        purged,
                        self.retention_days,
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.warning("Trace retention periódica falhou: %s", exc)

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                if item.stage == "__stop__" and self._stopping:
                    self._queue.task_done()
                    break
                await asyncio.to_thread(
                    self.store.insert_event,
                    trace_id=item.trace_id,
                    timestamp=item.timestamp,
                    service=item.service,
                    stage=item.stage,
                    data=item.data,
                    priority=item.priority,
                )
            except Exception as exc:
                log.warning("trace persist failed: %s", exc)
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass
