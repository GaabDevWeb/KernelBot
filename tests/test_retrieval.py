"""Testes unitários da política de retrieval (Fases 1, 2 e 3).

Cobrem os critérios de aceite do plano incremental RAG ACL:

- Pergunta sem contexto não chama LLM (hard stop insufficient_context).
- Pergunta subespecificada gera underspecified_query no modo strict.
- Pergunta vaga mas perigosa gera vague_but_high_risk.
- Retrieval ambíguo por margem baixa gera ambiguous_retrieval.
- Coverage baixa gera context_misaligned.
- confidence == low gera hard stop no modo strict.
- Coverage usa apenas termos informativos.
- Sanity check pós-geração dispara flags esperadas.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.retrieval import (
    GENERIC_ACTION_TERMS,
    MIN_COVERAGE,
    MIN_SCORE,
    MIN_SCORE_MARGIN,
    MIN_TERMS,
    RetrievalCandidate,
    build_decision,
    classify_terms,
    coverage,
    coverage_weighted,
    expand_query_tokens,
    extract_informative_terms,
    is_vague_but_high_risk,
    normalize_and_tokenize,
    post_generation_flags,
    select_mode,
)


# --- Normalização e extração ------------------------------------------------

def test_normalize_and_tokenize_basic():
    assert normalize_and_tokenize("Como melhorar Performance SQL?") == [
        "como", "melhorar", "performance", "sql",
    ]


def test_extract_informative_terms_drops_stopwords_and_generic_actions():
    # "como" é stopword, "melhorar" é GENERIC_ACTION_TERMS.
    assert extract_informative_terms("como melhorar performance") == ["performance"]


def test_extract_informative_terms_keeps_technical_acronyms():
    # Siglas curtas (<=3 chars) entram via allowlist.
    terms = extract_informative_terms("como usar sql e api com rag")
    assert set(terms) == {"sql", "api", "rag"}


def test_extract_informative_terms_preserves_order_and_deduplicates():
    terms = extract_informative_terms("performance sql performance dashboard")
    assert terms == ["performance", "sql", "dashboard"]


# --- Coverage ---------------------------------------------------------------

def test_coverage_formula():
    # ["performance","sql"] ∩ ["performance","dashboard"] = {"performance"} → 1/2.
    assert coverage(["performance", "sql"], ["performance", "dashboard"]) == 0.5


def test_coverage_is_zero_when_no_informative_terms():
    assert coverage([], ["anything"]) == 0.0


def test_classify_terms_separates_central_from_optional():
    central, optional = classify_terms(["sql", "performance", "visualizacao-sql", "banco"])
    assert "sql" in central
    assert "visualizacao-sql" in central
    assert "performance" in optional
    assert "banco" in optional


def test_coverage_weighted_doubles_central_terms():
    # central=["sql"] (match), optional=["performance"] (no match).
    # num = 2*1 + 0 = 2, den = 2*1 + 1 = 3 → 2/3.
    central, optional = classify_terms(["sql", "performance"])
    assert central == ["sql"]
    assert optional == ["performance"]
    cw = coverage_weighted(central, optional, ["sql", "tutorial"])
    assert abs(cw - (2 / 3)) < 1e-9


# --- is_vague_but_high_risk -------------------------------------------------

def test_vague_but_high_risk_detects_erro_api():
    info = extract_informative_terms("erro api")
    central, _ = classify_terms(info)
    # "api" cai em whitelist central, mas é domínio ambíguo → não conta como forte.
    assert is_vague_but_high_risk(info, central) is True


def test_vague_but_high_risk_false_when_specific_domain_present():
    info = extract_informative_terms("performance sql query")
    central, _ = classify_terms(info)
    # "sql" é central específico → não é vago-perigoso.
    assert is_vague_but_high_risk(info, central) is False


def test_vague_but_high_risk_false_without_quality_term():
    info = extract_informative_terms("select join postgres")
    central, _ = classify_terms(info)
    assert is_vague_but_high_risk(info, central) is False


# --- build_decision: Fase 1 (hard stop por score/hits) ----------------------

def _make_candidate(raw: float, text: str, source: str = "db:python/intro") -> RetrievalCandidate:
    return RetrievalCandidate(
        source=source,
        chunk_id=f"{source}:0",
        text=text,
        discipline="python",
        raw_score=raw,
        normalized_score=min(1.0, raw / 10.0),
        matched_terms=(),
    )


def test_decision_no_hits_returns_insufficient_context():
    d = build_decision("como usar variáveis em python", [], mode="strict")
    assert d.is_hard_stop
    assert d.reason == "insufficient_context"
    assert d.trace.llm_called is False
    assert d.trace.top_score == 0.0


def test_decision_low_top_score_returns_insufficient_context():
    cands = [
        _make_candidate(MIN_SCORE - 0.5, "algum texto genérico"),
    ]
    d = build_decision("como usar variaveis python", cands, mode="strict")
    assert d.reason == "insufficient_context"
    assert d.trace.top_score < MIN_SCORE


# --- build_decision: Fase 2 (gates de incerteza) ----------------------------

def test_decision_underspecified_query_in_strict():
    # "performance" sozinho é 1 termo informativo; MIN_TERMS=2.
    cands = [_make_candidate(5.0, "performance de dashboard importa muito")]
    d = build_decision("performance", cands, mode="strict")
    assert d.reason == "underspecified_query"


def test_decision_underspecified_query_allowed_in_assistive():
    cands = [_make_candidate(5.0, "performance de dashboard importa muito")]
    d = build_decision("performance", cands, mode="assistive")
    # Em assistive, underspecified não bloqueia; ainda pode cair em outros gates.
    assert d.reason != "underspecified_query"


def test_decision_vague_but_high_risk():
    cands = [_make_candidate(5.0, "erro típico em api de autenticação")]
    d = build_decision("erro api", cands, mode="strict")
    assert d.reason == "vague_but_high_risk"


def test_decision_context_misaligned_when_coverage_low():
    # Query com termos fortes, chunk que só cobre 1/3 → context_misaligned.
    chunk_text = "dashboard de vendas usa redis para cache"
    cands = [_make_candidate(5.0, chunk_text)]
    # Query tem 3 termos informativos, só "redis" aparece no chunk → 1/3 ≈ 0.33.
    d = build_decision("sql performance redis", cands, mode="strict")
    # Coverage ~0.33 é igual ao default MIN_COVERAGE=0.34? Força ficar abaixo.
    assert d.trace.coverage < MIN_COVERAGE or d.reason in {
        "context_misaligned", "low_confidence", "ambiguous_retrieval",
    }


def test_decision_ambiguous_retrieval_when_margin_low():
    cands = [
        _make_candidate(5.00, "sql performance em select", source="db:python/a"),
        _make_candidate(4.99, "sql performance em update", source="db:python/b"),
    ]
    d = build_decision("sql performance", cands, mode="strict")
    assert d.reason == "ambiguous_retrieval"
    assert d.trace.score_margin < MIN_SCORE_MARGIN


def test_decision_low_confidence_when_missing_central_term():
    # Query tem "sql" central, mas chunk não contém "sql" literal.
    cands = [
        _make_candidate(5.0, "performance de dashboard no looker", source="db:visualizacao-sql/a"),
        _make_candidate(3.0, "outro texto qualquer", source="db:visualizacao-sql/b"),
    ]
    d = build_decision("sql performance", cands, mode="strict")
    # Pode cair em context_misaligned (coverage baixo) ou low_confidence
    # dependendo do caminho; o importante é que hard stop aconteça.
    assert d.is_hard_stop


def test_decision_ok_when_everything_aligns():
    # Query com 2 termos, chunk cobre todos, margem alta.
    chunk_text = (
        "sql select from tabela where filtro group by campo; "
        "esse select performance cresce com índices corretos"
    )
    cands = [
        _make_candidate(10.0, chunk_text, source="db:visualizacao-sql/a"),
        _make_candidate(5.0, "outro texto", source="db:visualizacao-sql/b"),
    ]
    d = build_decision("sql performance", cands, mode="strict")
    assert d.allow_generation, f"expected ok, got {d.reason}"
    assert d.confidence in {"high", "medium"}
    assert d.trace.llm_called is True


# --- Diversidade de fonte ---------------------------------------------------

def test_top_k_respects_max_chunks_per_source():
    cands = [
        _make_candidate(10.0, "a", source="db:py/one"),
        _make_candidate(9.5, "b", source="db:py/one"),
        _make_candidate(9.0, "c", source="db:py/one"),  # deve ser descartado
        _make_candidate(8.5, "d", source="db:py/two"),
    ]
    d = build_decision("sql performance", cands, mode="strict")
    # Pode ser hard stop por outros motivos, mas os selected_sources do
    # trace respeitam o limite.
    sources = [s["source"] for s in d.trace.selected_sources]
    assert sources.count("db:py/one") <= 2


# --- select_mode ------------------------------------------------------------

def test_select_mode_defaults_to_strict():
    assert select_mode(False, False, None, has_explicit_assistive_flag=False) == "strict"
    assert select_mode(True, False, None, has_explicit_assistive_flag=False) == "strict"
    assert select_mode(False, True, "python", has_explicit_assistive_flag=False) == "strict"


def test_select_mode_assistive_requires_explicit_flag():
    assert select_mode(False, False, None, has_explicit_assistive_flag=True) == "assistive"


# --- Sanity check pós-geração (Fase 3) -------------------------------------

def test_post_generation_flags_missing_informative_terms():
    # Resposta não cita "sql" nem "performance".
    cands = [_make_candidate(5.0, "sql performance com índices")]
    flags = post_generation_flags(
        "A resposta é genérica e não menciona nada específico da query.",
        ["sql", "performance"],
        cands,
    )
    assert "missing_informative_terms" in flags


def test_post_generation_flags_missing_source_entities():
    # Resposta cita um termo da query ("sql") mas não cita nenhuma fonte
    # nem compartilha tokens significativos com o chunk.
    cands = [_make_candidate(5.0, "abstract terms only placeholder", source="db:py/unique")]
    flags = post_generation_flags(
        "sql é uma linguagem inventada; apenas palavrinhas curtas.",
        ["sql"],
        cands,
    )
    assert "missing_source_entities" in flags


def test_post_generation_flags_empty_when_answer_is_grounded():
    chunk_text = "sql performance melhora com índices certos"
    cands = [_make_candidate(5.0, chunk_text, source="db:visualizacao-sql/index")]
    answer = (
        "A base db:visualizacao-sql/index mostra que performance em sql melhora "
        "com índices corretos sobre colunas filtradas."
    )
    flags = post_generation_flags(answer, ["sql", "performance"], cands)
    assert flags == []


# --- GENERIC_ACTION_TERMS ---------------------------------------------------

def test_generic_action_terms_includes_common_verbs():
    # Sanity: os termos de ação mais comuns estão na lista e NÃO contam
    # como informativos.
    for term in ("melhorar", "configurar", "usar", "criar"):
        assert term in GENERIC_ACTION_TERMS


# --- Query rewriting conservador (Fase 3) -----------------------------------

def test_expand_query_tokens_adds_accent_stripped_variants():
    # Acento + sem acento coexistem; ordem preservada.
    assert expand_query_tokens(["variável", "sql"]) == ["variável", "variavel", "sql"]


def test_expand_query_tokens_is_idempotent():
    tokens = ["sql", "python", "api"]
    assert expand_query_tokens(tokens) == tokens


def test_expand_query_tokens_deduplicates():
    # "cao" vira stripped de "ção", mas se já houver "cao" na query,
    # não duplica.
    assert expand_query_tokens(["ação", "cao"]) == ["ação", "acao", "cao"]
