"""ContextRouter — decisão determinística FAST | NORMAL | DEEP (sem I/O / LLM).

Alinhado a optimization/routing.md e docs/contracts/context-route-v1.md.
"""

from __future__ import annotations

import re
import unicodedata

from kernel.context.institutional import SECTION_FILES
from kernel.context.types import (
    CalendarBudgets,
    ContextProfile,
    ContextRoute,
    RagSkipReason,
    RouteSignals,
)

_SECTION_BASENAMES: tuple[str, ...] = tuple(name for name, _ in SECTION_FILES)

_GREETING_ACK_RE = re.compile(
    r"^(oi+|ola|olá|hey|eai|e\s*ai|opa|obrigad[oa]|valeu|vlw|tmj|"
    r"t[aá]\s+on|bom\s+dia|boa\s+tarde|boa\s+noite)"
    r"[\s!.?]*$",
    re.IGNORECASE,
)

_DEEP_MARKER_RES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bexplica\b",
        r"\bexplique\b",
        r"\bdetalha\b",
        r"\bdetalhe\b",
        r"\bcompara\b",
        r"\bpor\s+que\b",
        r"\bporque\b",
        r"\bcom\s+base\s+(no|nos|na|nas|em)\b",
        r"\bmulti[- ]?hop\b",
    )
)

_DEIXIS_RES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(isso|isto|aquilo|aquele|aquela|aqueles|aquelas|desse|dessa|nele|nela)\b",
        r"^e\s+(o|a|os|as)\s+\w+",
        r"^e\s+\w+\?",
    )
)

_POLICY_RE = re.compile(
    r"\b(regras?|pol[ií]tica|proibid[oa]|permitid[oa]|faltas?|faltar|"
    r"presen[cç]a|posso\s+(faltar|entregar)|pode\s+entregar|"
    r"atraso|atrasad[oa]s?)\b",
    re.IGNORECASE,
)

_CALENDAR_TERM_RE = re.compile(
    r"\b(prova|provas|avaliacao|avaliacoes|avalia[cç][aã]o|entrega|entregas|"
    r"trabalho|trabalhos|seminario|semin[aá]rios|at|ats|aula|aulas|"
    r"evento|eventos|prazo|prazos|tp|tps|agenda)\b",
    re.IGNORECASE,
)

_ACADEMIC_CONTENT_RE = re.compile(
    r"\b(material|materiais|pdf|slide|slides|conte[uú]do|conceito|conceitos|"
    r"c[oó]digo|codigo|defini[cç][aã]o|explica|com\s+base|"
    r"list\s+comprehension|fun[cç][aã]o|classe|módulo|modulo)\b",
    re.IGNORECASE,
)

_PROFESSOR_HINT_RE = re.compile(
    r"\b(professor(?:a|es)?|marina|alan(?:\s+alonso)?|gesiel|marcelo|"
    r"kadu(?:z[aã]o)?|caduz[aã]o|vergili|hama)\b",
    re.IGNORECASE,
)

_DISCIPLINE_HINT_RE = re.compile(
    r"\b(python|sql|banco\s+de\s+dados|projeto\s+de\s+bloco|flu[eê]ncia|"
    r"visualiza[cç][aã]o|processamento\s+de\s+dados|modelagem)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _is_greeting_ack(normalized: str) -> bool:
    return bool(normalized and _GREETING_ACK_RE.match(normalized))


def _has_deep_markers(normalized: str, raw: str) -> bool:
    if any(p.search(normalized) for p in _DEEP_MARKER_RES):
        return True
    if raw.count("?") >= 2:
        return True
    # Query longa multi-hop (~> 120 chars com conector).
    if len(normalized) >= 120 and re.search(r"\b(e|também|tambem|depois|alem)\b", normalized):
        return True
    return False


def _has_deixis(normalized: str) -> bool:
    return any(p.search(normalized) for p in _DEIXIS_RES)


def _is_calendar_only(normalized: str, *, temporal_kind: str | None) -> bool:
    if temporal_kind != "calendar_fact" and not _CALENDAR_TERM_RE.search(normalized):
        return False
    if _ACADEMIC_CONTENT_RE.search(normalized):
        return False
    return temporal_kind == "calendar_fact" or bool(_CALENDAR_TERM_RE.search(normalized))


def _select_institutional_files(
    normalized: str,
    *,
    profile: ContextProfile,
) -> tuple[bool, tuple[str, ...]]:
    if profile is ContextProfile.FAST:
        if _PROFESSOR_HINT_RE.search(normalized):
            return True, ("professors.md",)
        if _DISCIPLINE_HINT_RE.search(normalized):
            return True, ("disciplines.md",)
        return False, ()

    if profile is ContextProfile.DEEP:
        return True, _SECTION_BASENAMES

    # NORMAL — selectivo
    files: list[str] = []
    if _POLICY_RE.search(normalized):
        files.append("rules.md")
    if _PROFESSOR_HINT_RE.search(normalized):
        files.append("professors.md")
    if _DISCIPLINE_HINT_RE.search(normalized):
        files.append("disciplines.md")
    # Preserva ordem canónica de SECTION_FILES.
    ordered = tuple(name for name in _SECTION_BASENAMES if name in files)
    return (bool(ordered), ordered)


def _budgets_for(profile: ContextProfile) -> CalendarBudgets:
    if profile is ContextProfile.FAST:
        return CalendarBudgets(max_events=0, max_past_events=0)
    if profile is ContextProfile.NORMAL:
        return CalendarBudgets(max_events=6, max_past_events=4)
    return CalendarBudgets(max_events=15, max_past_events=12)


class ContextRouter:
    """Router puro: query + sinais → ContextRoute."""

    def route(self, query: str, *, signals: RouteSignals) -> ContextRoute:
        raw = (query or "").strip()
        normalized = _normalize(raw)
        intent = signals.temporal_intent
        intent_kind = intent.kind if intent is not None else None
        reasons: list[str] = []

        policy_signal = bool(_POLICY_RE.search(normalized))

        # --- Prioridade top-down (routing.md) --------------------------------
        # Política institucional nunca fica em FAST puro (SEC-001/002):
        # time_fact + regras → NORMAL com rules.md.
        if signals.force_doc or signals.force_rag or signals.discipline_from_command:
            profile = ContextProfile.DEEP
            if signals.force_doc:
                reasons.append("force_doc")
            if signals.force_rag:
                reasons.append("force_rag")
            if signals.discipline_from_command:
                reasons.append("discipline_command")
        elif _has_deep_markers(normalized, raw):
            profile = ContextProfile.DEEP
            reasons.append("deep_markers")
        elif intent_kind == "time_fact" and not policy_signal:
            profile = ContextProfile.FAST
            reasons.append("time_fact")
        elif intent_kind == "time_fact" and policy_signal:
            profile = ContextProfile.NORMAL
            reasons.append("time_fact_with_policy")
        elif _is_greeting_ack(normalized):
            profile = ContextProfile.FAST
            reasons.append("greeting_ack")
        elif intent_kind == "calendar_fact":
            profile = ContextProfile.NORMAL
            reasons.append("calendar_fact")
        elif _has_deixis(normalized) or (
            signals.history_turns > 0 and len(normalized.split()) <= 6
        ):
            profile = ContextProfile.NORMAL
            reasons.append("deixis_followup")
        else:
            profile = ContextProfile.NORMAL
            reasons.append("default_academic")

        include_inst, inst_files = _select_institutional_files(
            normalized, profile=profile
        )
        if policy_signal and profile is not ContextProfile.FAST:
            # Garante rules.md mesmo quando outros sinais não seleccionaram ficheiros.
            files_list = list(inst_files)
            if "rules.md" not in files_list:
                files_list.append("rules.md")
            inst_files = tuple(name for name in _SECTION_BASENAMES if name in files_list)
            include_inst = True
            if "policy_rules" not in reasons:
                reasons.append("policy_rules")

        calendar_signal = intent_kind == "calendar_fact" or bool(
            _CALENDAR_TERM_RE.search(normalized)
        )
        if profile is ContextProfile.FAST:
            include_calendar = False
        elif profile is ContextProfile.DEEP:
            include_calendar = True
        else:
            include_calendar = calendar_signal

        budgets = _budgets_for(profile)
        if not include_calendar:
            budgets = CalendarBudgets(max_events=0, max_past_events=0)

        # Transcript
        if profile is ContextProfile.FAST:
            if intent_kind == "time_fact":
                turns = 0
            elif "greeting_ack" in reasons:
                turns = 1
            else:
                turns = 2
        elif profile is ContextProfile.NORMAL:
            if "deixis_followup" in reasons and signals.history_turns > 0:
                turns = 8
            elif intent_kind == "calendar_fact":
                turns = 4
            else:
                turns = 2
        else:
            turns = max(0, int(signals.chat_history_max_turns))

        # RAG
        rag_skipped = False
        rag_reason = RagSkipReason.NONE
        max_rag = 0
        filter_low = False

        if profile is ContextProfile.FAST:
            rag_skipped = True
            max_rag = 0
            filter_low = False
            if intent_kind == "time_fact":
                rag_reason = RagSkipReason.TEMPORAL_FACT
            elif "greeting_ack" in reasons:
                rag_reason = RagSkipReason.GREETING_ACK
            else:
                rag_reason = RagSkipReason.PROFILE_FAST
        elif profile is ContextProfile.NORMAL:
            filter_low = True
            # calendar_only incompatível com sinal de política (SEC-002).
            if (
                not policy_signal
                and _is_calendar_only(normalized, temporal_kind=intent_kind)
            ):
                rag_skipped = True
                rag_reason = RagSkipReason.CALENDAR_ONLY
                max_rag = 0
            else:
                rag_skipped = False
                rag_reason = RagSkipReason.NONE
                max_rag = 5
        else:  # DEEP
            rag_skipped = False
            rag_reason = RagSkipReason.NONE
            max_rag = 7
            filter_low = True

        # force_* / disciplina anulam skip (já forçam DEEP, mas reforço).
        if signals.force_doc or signals.force_rag or signals.discipline_from_command:
            rag_skipped = False
            rag_reason = RagSkipReason.NONE
            max_rag = max(max_rag, 7)

        return ContextRoute(
            profile=profile,
            include_identity=True,
            include_temporal=True,
            include_institutional=include_inst,
            institutional_files=inst_files,
            include_calendar=include_calendar,
            calendar_budgets=budgets,
            rag_skipped=rag_skipped,
            rag_skip_reason=rag_reason,
            transcript_max_turns=turns,
            max_rag_sources=max_rag,
            filter_low_confidence_rag=filter_low,
            reasons=tuple(reasons),
        )
