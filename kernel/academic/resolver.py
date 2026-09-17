"""Resolução determinística de referências académicas."""

from __future__ import annotations

import re

from kernel.academic.assessment_catalog import AssessmentCatalog
from kernel.academic.catalog import AcademicCatalog
from kernel.academic.intent import (
    detect_academic_intent,
    parse_assessment_item,
    parse_assessment_reference,
    parse_lesson_reference,
)
from kernel.academic.models import (
    AcademicIntent,
    AcademicReferenceKind,
    AcademicResolveResult,
)
from kernel.disciplines.disciplines import load_disciplines, trace_label_by_discipline
from kernel.knowledge.lesson_catalog import normalize_lesson_key

_TOPIC_TO_DISCIPLINE: dict[str, str] = {
    "java": "fundamentos-java",
    "csharp": "fundamentos-csharp",
    "c#": "fundamentos-csharp",
    "python": "python",
    "sql": "sql-modelagem-relacional",
    "backend": "projeto-bloco-backend",
    "carreira": "planejamento-curso-carreira",
}


def resolve_discipline_from_query(
    query: str,
    *,
    command_discipline: str | None = None,
    conversation_topic: str | None = None,
    catalog: AcademicCatalog | None,
) -> str | None:
    if command_discipline and catalog and catalog.lessons_for_discipline(command_discipline):
        return command_discipline.strip().lower()

    q = (query or "").lower()
    labels = trace_label_by_discipline()

    for disc in catalog.discipline_ids() if catalog else []:
        if disc in q or labels.get(disc, "").lower() in q:
            return disc

    for cfg in load_disciplines():
        if cfg.id in q or cfg.label.lower() in q:
            return cfg.id
        for marker in cfg.query_markers:
            if marker.lower() in q:
                return cfg.id

    if conversation_topic:
        mapped = _TOPIC_TO_DISCIPLINE.get(conversation_topic.lower())
        if mapped and catalog and catalog.lessons_for_discipline(mapped):
            return mapped

    if catalog and len(catalog.discipline_ids()) == 1:
        return catalog.discipline_ids()[0]

    return None


def _prompt_block_for_assessment(
    *,
    entry,
    intent: AcademicIntent,
    discipline_label: str,
    item_number: int | None = None,
) -> str:
    kind_label = entry.kind.upper()
    if entry.number is not None:
        kind_label = f"{kind_label} {entry.number}"
    lines = [
        "## Avaliação resolvida (catálogo — determinístico)",
        f"- Disciplina: **{discipline_label}** (`{entry.discipline}`)",
        f"- {kind_label}: **{entry.title}**",
    ]
    if entry.due_date:
        lines.append(f"- Data de entrega: {entry.due_date}")
    if entry.url:
        lines.append(f"- URL Moodle: {entry.url}")
    lines.append(f"- Fonte indexada: `{entry.source}`")
    if intent == AcademicIntent.ASSESSMENT_EXPLAIN:
        content = entry.read_content()
        if content:
            lines.append("\n### Enunciado (material real indexado)\n")
            lines.append(content)
        if item_number is not None:
            lines.append(
                f"\n**Foco:** o utilizador perguntou sobre questão/exercício **{item_number}**. "
                f"Localize no enunciado a secção **Exercício {item_number}** (ou Parte {item_number}) "
                "e responda com base só nela — não generalize nem invente."
            )
        lines.append(
            "\n**Instrução:** responda com base no enunciado acima. "
            "Não invente requisitos, prazos nem links. Não remeta ao Moodle se o enunciado já está aqui."
        )
    else:
        lines.append(
            "\n**Instrução:** o utilizador pediu o TP/AT. Confirme título, prazo e "
            "como aceder (URL acima se existir). Não invente enunciado completo se não pediu explicação."
        )
    return "\n".join(lines)


def _prompt_block_for_lesson(
    *,
    lesson,
    intent: AcademicIntent,
    reference_kind: AcademicReferenceKind | None,
    discipline_label: str,
) -> str:
    lines = [
        "## Contexto académico resolvido (catálogo — determinístico)",
        f"- Disciplina: **{discipline_label}** (`{lesson.discipline}`)",
        f"- Aula {lesson.order}: **{lesson.title}**",
        f"- Slug: `{lesson.slug}`",
        f"- Fonte RAG: `{lesson.source}`",
    ]
    if lesson.url:
        lines.append(f"- URL ISS: {lesson.url}")
    if intent == AcademicIntent.LINK_ONLY:
        lines.append(
            "\n**Instrução:** o utilizador pediu o link. Responda com o título da aula e a URL "
            "acima. Não invente outro link."
        )
    elif intent == AcademicIntent.CONTENT:
        lines.append(
            "\n**Instrução:** use os trechos RAG desta aula como base factual para responder. "
            "A identificação da aula já está resolvida — não adivinhe outra."
        )
    elif intent == AcademicIntent.NAVIGATION:
        kind = reference_kind.value if reference_kind else "navigation"
        lines.append(
            f"\n**Instrução:** referência académica `{kind}` resolvida. "
            "Responda com base nos metadados e trechos RAG desta aula."
        )
    return "\n".join(lines)


def _combined_assessment_context(
    query: str,
    recent_queries: tuple[str, ...] | None,
) -> str:
    parts = [q.strip() for q in (recent_queries or ()) if (q or "").strip()]
    if (query or "").strip():
        parts.append(query.strip())
    return " ".join(parts)


def _resolve_assessment_from_context(
    query: str,
    *,
    recent_queries: tuple[str, ...] | None,
    command_discipline: str | None,
    conversation_topic: str | None,
    catalog: AcademicCatalog | None,
) -> tuple[str, int | None, str | None, int | None]:
    """(kind, number, discipline, item_number) a partir da query + histórico recente."""
    combined = _combined_assessment_context(query, recent_queries)
    item_number = parse_assessment_item(query) or parse_assessment_item(combined)
    parsed = parse_assessment_reference(combined) or parse_assessment_reference(query or "")
    if parsed:
        kind, number = parsed
    elif item_number is not None:
        kind, number = "assessment", None
    else:
        kind, number = "assessment", None
    discipline = resolve_discipline_from_query(
        combined,
        command_discipline=command_discipline,
        conversation_topic=conversation_topic,
        catalog=catalog,
    )
    if discipline is None and (query or "").strip():
        discipline = resolve_discipline_from_query(
            query,
            command_discipline=command_discipline,
            conversation_topic=conversation_topic,
            catalog=catalog,
        )
    return kind, number, discipline, item_number


def resolve_academic_query(
    query: str,
    *,
    catalog: AcademicCatalog | None,
    assessment_catalog: AssessmentCatalog | None = None,
    command_discipline: str | None = None,
    conversation_topic: str | None = None,
    pinned_lesson_key: str | None = None,
    recent_queries: tuple[str, ...] | None = None,
) -> AcademicResolveResult:
    if catalog is None or not (query or "").strip():
        return AcademicResolveResult(resolved=False, reason="catalog_unavailable")

    intent = detect_academic_intent(query)
    item_in_query = parse_assessment_item(query) is not None
    combined = _combined_assessment_context(query, recent_queries)
    has_assessment_context = bool(
        parse_assessment_reference(combined)
        or parse_assessment_item(combined)
        or re.search(r"\b(?:at|tp|assessment)\b", combined, re.IGNORECASE)
    )
    if intent == AcademicIntent.NONE and item_in_query and has_assessment_context:
        intent = AcademicIntent.ASSESSMENT_EXPLAIN
    if intent == AcademicIntent.NONE and (query or "").strip().lower() in {
        "java",
        "csharp",
        "c#",
        "python",
        "backend",
        "sql",
    }:
        if has_assessment_context and parse_assessment_item(combined):
            intent = AcademicIntent.ASSESSMENT_EXPLAIN

    if intent == AcademicIntent.NONE:
        return AcademicResolveResult(resolved=False, reason="no_academic_intent")

    discipline = resolve_discipline_from_query(
        query,
        command_discipline=command_discipline,
        conversation_topic=conversation_topic,
        catalog=catalog,
    )

    if intent in (AcademicIntent.ASSESSMENT_LOOKUP, AcademicIntent.ASSESSMENT_EXPLAIN):
        kind, number, disc_from_ctx, item_number = _resolve_assessment_from_context(
            query,
            recent_queries=recent_queries,
            command_discipline=command_discipline,
            conversation_topic=conversation_topic,
            catalog=catalog,
        )
        discipline = discipline or disc_from_ctx
        if intent == AcademicIntent.ASSESSMENT_LOOKUP and (
            item_number is not None or re.search(r"\bcobrad", query, re.IGNORECASE)
        ):
            intent = AcademicIntent.ASSESSMENT_EXPLAIN
        if discipline is None:
            return AcademicResolveResult(
                resolved=False,
                intent=intent,
                missing_data=True,
                reason="discipline_unresolved_for_assessment",
                prompt_block=(
                    "## Avaliação (TP/AT)\n"
                    "Não foi possível determinar a disciplina. Peça ao utilizador para indicar "
                    f"o módulo/comando (ex.: `/java`) antes de localizar o {kind.upper()}."
                ),
            )
        ac = assessment_catalog or AssessmentCatalog.empty()
        entry = ac.resolve(discipline, kind=kind, number=number)
        if entry is None:
            return AcademicResolveResult(
                resolved=False,
                intent=intent,
                missing_data=True,
                discipline=discipline,
                reason="assessment_not_indexed",
                prompt_block=(
                    f"## Avaliação ({kind.upper()})\n"
                    f"Não encontrei {kind.upper()}"
                    f"{f' {number}' if number else ''} em `{discipline}`. "
                    "Informe ao utilizador de forma directa — não invente enunciados nem links."
                ),
                metadata={"assessment_kind": kind, "assessment_number": number},
            )
        disc_label = trace_label_by_discipline().get(discipline, discipline)
        return AcademicResolveResult(
            resolved=True,
            intent=intent,
            reference_kind=AcademicReferenceKind.ASSESSMENT,
            discipline=discipline,
            assessment=entry,
            prompt_block=_prompt_block_for_assessment(
                entry=entry,
                intent=intent,
                discipline_label=disc_label,
                item_number=item_number,
            ),
            metadata={
                "assessment_kind": entry.kind,
                "assessment_number": entry.number,
                "assessment_slug": entry.slug,
                "assessment_source": entry.source,
                "assessment_item": item_number,
            },
        )

    ref_kind, order_num = parse_lesson_reference(query)
    if ref_kind is None:
        return AcademicResolveResult(resolved=False, intent=intent, reason="reference_unparsed")

    if discipline is None:
        return AcademicResolveResult(
            resolved=False,
            intent=intent,
            ambiguous=True,
            reason="discipline_unresolved",
            prompt_block=(
                "## Referência académica ambígua\n"
                "Não foi possível determinar a disciplina. Peça reformulação com módulo "
                "ou comando (ex.: `/java`, `/csharp`)."
            ),
        )

    labels = trace_label_by_discipline()
    disc_label = labels.get(discipline, discipline)
    lesson = None

    if ref_kind == AcademicReferenceKind.FIRST:
        lesson = catalog.first_lesson(discipline)
    elif ref_kind == AcademicReferenceKind.LAST:
        lesson = catalog.last_lesson(discipline)
    elif ref_kind == AcademicReferenceKind.BY_ORDER and order_num is not None:
        lesson = catalog.lesson_by_order(discipline, order_num)
    elif ref_kind == AcademicReferenceKind.LINK and order_num is not None:
        lesson = catalog.lesson_by_order(discipline, order_num)
        intent = AcademicIntent.LINK_ONLY
    elif ref_kind in (AcademicReferenceKind.PREVIOUS, AcademicReferenceKind.NEXT):
        anchor_slug: str | None = None
        anchor_order: int | None = None
        if pinned_lesson_key and ":" in pinned_lesson_key:
            _, anchor_slug = pinned_lesson_key.split(":", 1)
        m = re.search(r"\baula\s+(?:n[ºo°]?\s*)?(\d{1,2})\b", query, re.IGNORECASE)
        if m:
            anchor_order = int(m.group(1))
        direction = "previous" if ref_kind == AcademicReferenceKind.PREVIOUS else "next"
        lesson = catalog.adjacent_lesson(
            discipline,
            slug=anchor_slug,
            order=anchor_order,
            direction=direction,
        )

    if lesson is None:
        return AcademicResolveResult(
            resolved=False,
            intent=intent,
            discipline=discipline,
            reference_kind=ref_kind,
            missing_data=True,
            reason="lesson_not_found",
            prompt_block=(
                f"## Catálogo académico\n"
                f"Não encontrei a aula pedida em **{disc_label}**. "
                "Informe ao utilizador de forma directa — não invente slug, ordem ou URL."
            ),
        )

    map_block = catalog.build_map_prompt_section(discipline)
    prompt = _prompt_block_for_lesson(
        lesson=lesson,
        intent=intent,
        reference_kind=ref_kind,
        discipline_label=disc_label,
    )
    if map_block:
        prompt = f"{prompt}\n\n{map_block}"

    return AcademicResolveResult(
        resolved=True,
        intent=intent,
        reference_kind=ref_kind,
        discipline=discipline,
        lesson=lesson,
        prompt_block=prompt,
        metadata={
            "lesson_order": lesson.order,
            "lesson_slug": lesson.slug,
            "lesson_url": lesson.url,
            "lesson_source": lesson.source,
            "lesson_key": normalize_lesson_key(lesson.discipline, lesson.slug),
        },
    )
