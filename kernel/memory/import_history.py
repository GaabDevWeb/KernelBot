"""CLI de importação de histórico de grupo (runtime — dados privados fora do Git).

Uso:
  python -m kernel.memory.import_history \\
    --file /caminho/externo/export.txt \\
    --platform whatsapp \\
    --channel-id 120363...@g.us

Nunca commitar o .txt real. Preferir `data/messages/` (gitignored).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from kernel.config import Settings
from kernel.memory.group_memory import GroupMemoryStore
from kernel.memory.whatsapp_import import (
    messages_to_store_payload,
    parse_whatsapp_export_file,
)

log = logging.getLogger("kernelbots.memory.import")


def _run_benchmark(store: GroupMemoryStore, platform: str, channel_id: str, queries: list[str]) -> dict:
    latencies: list[float] = []
    hits = 0
    for q in queries:
        t0 = time.perf_counter()
        res = store.search_historical(platform, channel_id, q, top_k=5)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        hits += len(res)
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    return {
        "queries": len(queries),
        "total_hits": hits,
        "latency_ms_avg": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "latency_ms_p95": round(p95, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importar histórico WhatsApp (.txt) → Group Memory SQLite")
    parser.add_argument("--file", required=True, help="Caminho absoluto ou relativo ao export .txt (privado)")
    parser.add_argument("--platform", default="whatsapp")
    parser.add_argument("--channel-id", required=True, help="ID do canal/grupo (ex. JID @g.us)")
    parser.add_argument("--db", default="", help="Override KERNEL_GROUP_MEMORY_DB_PATH")
    parser.add_argument("--dry-run", action="store_true", help="Só parse + stats, sem gravar")
    parser.add_argument("--benchmark", action="store_true", help="Medir buscas após import")
    parser.add_argument("--encoding", default="utf-8")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    export_path = Path(args.file).expanduser().resolve()
    if not export_path.is_file():
        log.error("Ficheiro não encontrado: %s", export_path)
        return 1

    t0 = time.perf_counter()
    parsed, stats = parse_whatsapp_export_file(
        export_path, channel_id=args.channel_id, encoding=args.encoding
    )
    parse_ms = (time.perf_counter() - t0) * 1000.0

    report = {
        "file": str(export_path),
        "platform": args.platform,
        "channel_id": args.channel_id,
        "dry_run": args.dry_run,
        "parse_ms": round(parse_ms, 2),
        "stats": stats.__dict__,
        "messages_ready": len(parsed),
    }

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    settings = Settings.load()
    db_path = Path(args.db) if args.db else (settings.group_memory_db_path or settings.project_root / "data" / "group_memory.sqlite3")
    store = GroupMemoryStore(db_path)

    before = store.count_messages(args.platform, args.channel_id)
    payload = messages_to_store_payload(parsed, platform=args.platform, channel_id=args.channel_id)

    t1 = time.perf_counter()
    inserted = store.record_messages_batch(payload)
    import_ms = (time.perf_counter() - t1) * 1000.0
    after = store.count_messages(args.platform, args.channel_id)

    report.update(
        {
            "db_path": str(db_path),
            "messages_before": before,
            "messages_after": after,
            "batch_inserted": inserted,
            "import_ms": round(import_ms, 2),
            "idempotent_delta": after - before,
        }
    )

    if args.benchmark and after > 0:
        sample_queries = [
            "prova",
            "trabalho",
            "recursividade",
            "professor",
            "entrega",
        ]
        report["benchmark"] = _run_benchmark(store, args.platform, args.channel_id, sample_queries)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
