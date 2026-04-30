"""
Orquestrador CLI do pipeline de ingestão.

Uso:
    python ingestion/run.py                          # todas as disciplinas
    python ingestion/run.py --discipline python      # filtra accordion por nome
    python ingestion/run.py --limit 5                # máximo 5 aulas novas
    python ingestion/run.py --no-headless            # abre browser visível (debug)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Garante que o root do projeto está no sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core.config import Settings
from engine.database import get_all_existing_orders
from ingestion.processor import process_transcription
from ingestion.scraper import scrape
from ingestion.sender import send_to_webhook


async def run(discipline_filter: str | None, limit: int | None, headless: bool) -> None:
    if discipline_filter:
        print(f"🔍  Coletando transcrições — filtro={discipline_filter!r}, limit={limit}")
    else:
        print(f"🔍  Coletando transcrições — todas as disciplinas, limit={limit}")

    settings = Settings.load()
    skip_orders = get_all_existing_orders(settings)
    total_existing = sum(len(v) for v in skip_orders.values())
    if total_existing:
        print(f"ℹ  {total_existing} aula(s) já no banco — serão ignoradas durante o scraping.")

    lessons = await scrape(
        limit=limit,
        headless=headless,
        discipline_filter=discipline_filter,
        skip_orders=skip_orders,
    )
    if not lessons:
        print("⚠  Nenhuma transcrição nova coletada.")
        return

    inserted = 0
    errors = 0

    for lesson in lessons:
        print(f"\n⚙️   Processando: {lesson.title!r} [{lesson.discipline}]...")
        try:
            processed = await process_transcription(lesson.raw_text, lesson.title)
        except Exception as exc:
            print(f"   ❌  Erro no processamento: {exc}")
            errors += 1
            continue

        try:
            result = await send_to_webhook(
                slug=lesson.slug,
                discipline=lesson.discipline,
                title=lesson.title,
                order=lesson.order,
                processed=processed,
            )
        except Exception as exc:
            print(f"   ❌  Erro ao enviar para webhook: {exc}")
            errors += 1
            continue

        status = result.get("status", "?")
        row_id = result.get("id", "?")

        if status == "inserted":
            print(f"   ✅  {lesson.title!r} → inserido (id={row_id})")
            inserted += 1
        elif status == "updated":
            print(f"   🔄  {lesson.title!r} → atualizado (id={row_id})")
            inserted += 1
        else:
            print(f"   ⚠   {lesson.title!r} → resposta inesperada: {result}")
            errors += 1

    print(f"\n{'─'*50}")
    print(f"✅  {inserted} inserida(s) / atualizada(s)   ❌  {errors} erro(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de ingestão de transcrições")
    parser.add_argument("--discipline", default=None, help="Filtra por nome do accordion (substring, case-insensitive)")
    parser.add_argument("--limit", type=int, default=None, help="Limite de aulas novas a processar")
    parser.add_argument("--no-headless", action="store_true", help="Abre browser visível (debug)")
    args = parser.parse_args()

    asyncio.run(run(
        discipline_filter=args.discipline,
        limit=args.limit,
        headless=not args.no_headless,
    ))


if __name__ == "__main__":
    main()
