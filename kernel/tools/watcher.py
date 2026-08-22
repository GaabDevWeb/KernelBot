"""Watchdog com debounce para rebuild do SearchEngine."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from engine.search import SearchEngine

log = logging.getLogger(f"kernelbots.{__name__}")


class ContentWatcher(FileSystemEventHandler):
    def __init__(self, search_engine: SearchEngine) -> None:
        super().__init__()
        self._search_engine = search_engine
        self._timer: threading.Timer | None = None

    def _debounced_rebuild(self) -> None:
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
            log.debug("   ↩  Rebuild anterior cancelado (debounce)")
        self._timer = threading.Timer(1.5, self._search_engine.rebuild)
        self._timer.start()

    def on_modified(self, event) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            filename = Path(event.src_path).name
            log.info(f"👁  Watchdog: modificação em '{filename}' — rebuild agendado em 1.5s")
            self._debounced_rebuild()

    def on_created(self, event) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            filename = Path(event.src_path).name
            log.info(f"👁  Watchdog: novo arquivo detectado '{filename}' — rebuild agendado em 1.5s")
            self._debounced_rebuild()

    def on_deleted(self, event) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            filename = Path(event.src_path).name
            log.info(f"👁  Watchdog: arquivo removido '{filename}' — rebuild agendado em 1.5s")
            self._debounced_rebuild()


def start_content_observer(search_engine: SearchEngine, content_dir: Path) -> Observer:
    observer = Observer()
    observer.schedule(ContentWatcher(search_engine), str(content_dir), recursive=True)
    observer.start()
    log.info(f"👁  Watchdog ativo — monitorando: {content_dir}")
    return observer
