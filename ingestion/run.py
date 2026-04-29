"""
Orquestrador CLI do pipeline de ingestão.

Uso:
    python ingestion/run.py --discipline python
    python ingestion/run.py --discipline python --limit 5
    python ingestion/run.py --discipline python --no-headless   # abre browser visível
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Garante que o root do projeto está no sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from ingestion.processor import process_transcription
from ingestion.scraper import scrape
from ingestion.sender import send_to_webhook


async def run(discipline: str, limit: int | None, headless: bool) -> None:
    print(f"🔍  Coletando transcrições — discipline={discipline!r}, limit={limit}")

    lessons = await scrape(limit=limit, headless=headless)
    if not lessons:
        print("⚠  Nenhuma transcrição coletada.")
        return

    inserted = 0
    skipped = 0

    for lesson in lessons:
        print(f"\n⚙️   Processando: {lesson.title!r}...")
        try:
            processed_content = await process_transcription(lesson.raw_text, lesson.title)
        except Exception as exc:
            print(f"   ❌  Erro no processamento: {exc}")
            continue

        try:
            result = await send_to_webhook(
                slug=lesson.slug,
                discipline=discipline,
                title=lesson.title,
                order=lesson.order,
                content=processed_content,
                raw_text=lesson.raw_text,
                source_url=lesson.url,
            )
        except Exception as exc:
            print(f"   ❌  Erro ao enviar para webhook: {exc}")
            continue

        status = result.get("status", "?")
        row_id = result.get("id", "?")

        if status == "ok":
            print(f"   ✅  {lesson.title!r} → id={row_id}")
            inserted += 1
        elif status == "unchanged":
            print(f"   ⏭   {lesson.title!r} → sem mudança (id={row_id})")
            skipped += 1
        else:
            print(f"   ⚠   {lesson.title!r} → resposta inesperada: {result}")

    print(f"\n{'─'*50}")
    print(f"✅  {inserted} inserida(s) / atualizada(s)   ⏭  {skipped} ignorada(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de ingestão de transcrições")
    parser.add_argument("--discipline", required=True, help="Disciplina (ex: python, visualizacao-sql)")
    parser.add_argument("--limit", type=int, default=None, help="Limite de aulas a processar")
    parser.add_argument("--no-headless", action="store_true", help="Abre browser visível (debug)")
    args = parser.parse_args()

    asyncio.run(run(
        discipline=args.discipline,
        limit=args.limit,
        headless=not args.no_headless,
    ))


if __name__ == "__main__":
    main()
