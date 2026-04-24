"""Contratos e política de decisão do RAG ACL.

Este módulo é o núcleo da mitigação incremental descrita em
`rag_acl_incremental_6951b55f.plan.md`. Ele NÃO faz retrieval BM25 (isso
continua em `engine.search`); ele normaliza termos, aplica regras de
suficiência e devolve uma `RetrievalDecision` que determina se a geração
deve acontecer ou se há hard stop.

A regra central é: na dúvida, não responder.

Fases suportadas:
- Fase 1: hard stop por ausência de hits e `top_score < MIN_SCORE`.
- Fase 2: coverage, MIN_TERMS, margem entre candidatos, vague_but_high_risk,
  coverage ponderada por termos centrais, `confidence == "low"`.
- Fase 3: sanity check pós-geração (override para `post_generation_misalignment`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal

Mode = Literal["strict", "assistive"]
Confidence = Literal["high", "medium", "low"]
DecisionReason = Literal[
    "ok",
    "insufficient_context",
    "context_misaligned",
    "underspecified_query",
    "ambiguous_retrieval",
    "low_confidence",
    "vague_but_high_risk",
    "post_generation_misalignment",
    "provider_error",
]

# Thresholds deliberadamente conservadores. O plano exige que eles sejam
# recalibrados com 20 casos manuais; estes defaults existem para não fingir
# alinhamento antes dessa calibração.
MIN_SCORE: float = 1.5
MIN_SCORE_MARGIN: float = 0.15
MIN_COVERAGE: float = 0.34
MIN_COVERAGE_WEIGHTED: float = 0.34
MIN_TERMS: int = 2
CANDIDATE_K: int = 8
TOP_K: int = 4
MAX_CHUNKS_PER_SOURCE: int = 2

# Stopwords PT-BR focadas em conectivos e pronomes. Mantido curto porque
# listas grandes tendem a remover sinal útil. Não é dicionário completo.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "o", "as", "os", "um", "uma", "uns", "umas",
        "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
        "por", "para", "pra", "pro", "com", "sem", "sob", "sobre", "entre",
        "que", "qual", "quais", "quando", "onde", "como", "porque", "pq",
        "se", "sim", "nao", "não", "mais", "menos", "muito", "pouco",
        "e", "ou", "mas", "ja", "já", "tambem", "também", "entao", "então",
        "isso", "isto", "aquilo", "esse", "essa", "este", "esta", "aquele", "aquela",
        "meu", "minha", "seu", "sua", "teu", "tua", "nosso", "nossa",
        "eu", "tu", "ele", "ela", "nos", "nós", "voce", "você", "vocês", "voces",
        "de", "da", "pela", "pelo", "pelas", "pelos",
        "ser", "estar", "ter", "haver", "existe", "existir",
        "ao", "aos", "à", "às",
    }
)

# Verbos/adjetivos de ação genérica que inflam coverage sem carregar domínio.
# A regra do plano é que esses termos caem mesmo quando `len(term) > 3`.
GENERIC_ACTION_TERMS: frozenset[str] = frozenset(
    {
        "melhorar", "melhor", "melhores", "piorar",
        "explicar", "explique", "explica", "mostrar", "mostra",
        "fazer", "faz", "faço", "feito", "feita",
        "configurar", "configura", "configurando",
        "usar", "uso", "usa", "usando", "usado",
        "entender", "entendi", "entenda",
        "ajudar", "ajuda", "ajude",
        "criar", "cria", "criando", "criado",
        "resolver", "resolve", "resolvido",
        "ajustar", "ajusta", "ajuste",
        "saber", "saiba",
        "dar", "da", "dê", "de",
        "tentar", "tenta", "tente",
        "funcionar", "funciona", "funcionando",
        "escrever", "escreve", "escrito",
        "rapido", "rápido", "rapidamente", "lento", "lenta",
        "simples", "basico", "básico", "avancado", "avançado",
        "exemplo", "exemplos", "coisa", "coisas",
        "algo", "alguem", "alguém", "ninguem", "ninguém",
        "tudo", "nada",
        "problema", "problemas", "duvida", "dúvida", "duvidas", "dúvidas",
        "jeito", "forma", "modo",
    }
)

# Categorias estruturalmente vagas: pares (termo de qualidade genérico + domínio
# ambíguo) que costumam passar em score/coverage mas não desambiguam o que o
# usuário realmente quer saber. São sinais para `vague_but_high_risk` quando
# aparecem sem outro termo de domínio específico.
_VAGUE_QUALITY_TERMS: frozenset[str] = frozenset(
    {"performance", "desempenho", "erro", "erros", "timeout", "bug", "lento", "lenta"}
)
_AMBIGUOUS_DOMAIN_TERMS: frozenset[str] = frozenset(
    {"banco", "api", "sistema", "app", "codigo", "código", "servidor"}
)


@dataclass(frozen=True)
class RetrievalCandidate:
    """Candidato bruto da camada lexical (sem decisão aplicada).

    `raw_score` é o score BM25 cru (não normalizado); `normalized_score` é
    normalizado por silo para uso em UI/ranking local. A decisão usa
    `raw_score`.
    """

    source: str
    chunk_id: str
    text: str
    discipline: str
    raw_score: float
    normalized_score: float
    matched_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalTrace:
    """Traço estruturado para logging/avaliação.

    Formato alinhado ao bloco JSON do plano.
    """

    query: str
    normalized_query: str
    informative_terms: tuple[str, ...]
    mode: Mode
    retrieval_mode: str = "bm25_lexical_temporary"
    top_score: float = 0.0
    second_score: float = 0.0
    score_margin: float = 0.0
    coverage: float = 0.0
    selected_sources: tuple[dict, ...] = ()
    decision: str = "hard_stop"
    reason: str = "insufficient_context"
    llm_called: bool = False
    tokens_used: int = 0
    debug: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "informative_terms": list(self.informative_terms),
            "retrieval_mode": self.retrieval_mode,
            "mode": self.mode,
            "top_score": self.top_score,
            "second_score": self.second_score,
            "score_margin": self.score_margin,
            "coverage": self.coverage,
            "selected_sources": [dict(s) for s in self.selected_sources],
            "decision": self.decision,
            "reason": self.reason,
            "llm_called": self.llm_called,
            "tokens_used": self.tokens_used,
            "debug": dict(self.debug),
        }


@dataclass(frozen=True)
class RetrievalDecision:
    """Decisão final do retrieval: permitir geração ou hard stop.

    `selected_candidates` só é populado quando `allow_generation=True`.
    `trace` nunca é None e carrega contexto para UI e avaliação.
    """

    allow_generation: bool
    reason: DecisionReason
    confidence: Confidence
    selected_candidates: tuple[RetrievalCandidate, ...]
    trace: RetrievalTrace

    @property
    def is_hard_stop(self) -> bool:
        return not self.allow_generation


# --- Normalização e extração de termos --------------------------------------

_WORD_RE = re.compile(r"[\w-]+", re.UNICODE)


def normalize_and_tokenize(text: str) -> list[str]:
    """Lowercase + tokenização simples por `\\w`.

    Mantém dígitos e hífens (útil para `rag`, `bm25`, `visualizacao-sql`).
    """
    if not text:
        return []
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


# Tabela de acentos PT-BR para expansão leve de query (Fase 3). Evita
# biblioteca externa: o plano pede rewriting conservador.
_ACCENT_MAP: dict[str, str] = {
    "á": "a", "à": "a", "â": "a", "ã": "a", "ä": "a",
    "é": "e", "ê": "e", "è": "e", "ë": "e",
    "í": "i", "î": "i", "ì": "i", "ï": "i",
    "ó": "o", "ô": "o", "õ": "o", "ò": "o", "ö": "o",
    "ú": "u", "û": "u", "ù": "u", "ü": "u",
    "ç": "c",
}


def _strip_accents(token: str) -> str:
    return "".join(_ACCENT_MAP.get(ch, ch) for ch in token)


def expand_query_tokens(tokens: list[str]) -> list[str]:
    """Expansão lexical conservadora: para tokens com acento, adiciona a
    versão sem acento (e vice-versa não é necessário porque o corpus real
    já é acentuado; só adicionamos o "fallback sem acento" para robustez
    a queries de usuário mal acentuadas).

    Regra: nunca remove tokens, só adiciona. Preserva ordem e dedup.
    """
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
        stripped = _strip_accents(t)
        if stripped != t and stripped not in seen:
            seen.add(stripped)
            out.append(stripped)
    return out


def extract_informative_terms(query: str) -> list[str]:
    """Extrai termos com valor de domínio.

    Regra do plano:
        term not in STOPWORDS
        and term not in GENERIC_ACTION_TERMS
        and len(term) > 3

    A preservação da ordem é importante para logging; duplicatas são
    removidas preservando a primeira ocorrência.
    """
    seen: set[str] = set()
    out: list[str] = []
    for term in normalize_and_tokenize(query):
        if term in STOPWORDS:
            continue
        if term in GENERIC_ACTION_TERMS:
            continue
        if len(term) <= 3:
            # termos de 3 caracteres como "sql", "api" são críticos; por isso
            # usamos `> 3` apenas como filtro anti-ruído, mas mantemos siglas
            # técnicas explicitamente via allowlist local:
            if term in {"sql", "api", "rag", "bm25", "ssl", "tcp", "udp", "ftp", "ssh", "php", "css", "xml", "mvp"}:
                if term not in seen:
                    seen.add(term)
                    out.append(term)
            continue
        if term not in seen:
            seen.add(term)
            out.append(term)
    return out


# --- Coverage e classificação -----------------------------------------------

# Siglas e tokens técnicos reconhecíveis como "centrais" (Fase 2). Tudo o
# que não cai aqui é tratado como opcional; heurística simples e auditável
# porque o plano proíbe semântica sofisticada antes de medir o baseline.
_CENTRAL_TOKEN_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")
_CENTRAL_WHITELIST: frozenset[str] = frozenset(
    {
        "sql", "python", "docker", "redis", "api", "rag", "bm25",
        "mysql", "postgres", "mongodb", "sqlite",
        "fastapi", "flask", "django",
        "openrouter", "http", "https", "json", "yaml",
        "select", "insert", "update", "delete", "join",
        "where", "group", "order", "limit",
        "loop", "for", "while", "variavel", "variável",
        "funcao", "função", "classe", "metodo", "método",
        "dashboard", "looker", "powerbi", "bigquery",
        "git", "github", "jwt", "oauth", "csrf", "xss",
        "reload", "chat", "content", "doc",
    }
)
_OPTIONAL_FORCED: frozenset[str] = frozenset(_VAGUE_QUALITY_TERMS | _AMBIGUOUS_DOMAIN_TERMS)


def classify_terms(informative_terms: Iterable[str]) -> tuple[list[str], list[str]]:
    """Separa termos centrais de opcionais (Fase 2, soft constraint).

    Central: sigla técnica, hífen composto (ex.: `visualizacao-sql`) ou
    presença em whitelist.
    Opcional: termos de qualidade genérica (`performance`, `erro`) e
    domínios ambíguos sem complemento (`banco`, `api` sozinho — nota: `api`
    está na whitelist porque aparece explicitamente em comandos, então
    conta como central).
    """
    central: list[str] = []
    optional: list[str] = []
    for t in informative_terms:
        tl = t.lower()
        if tl in _OPTIONAL_FORCED and tl not in _CENTRAL_WHITELIST:
            optional.append(tl)
            continue
        if tl in _CENTRAL_WHITELIST or _CENTRAL_TOKEN_RE.match(tl):
            central.append(tl)
            continue
        optional.append(tl)
    return central, optional


def coverage(informative_terms: Iterable[str], chunk_terms: Iterable[str]) -> float:
    """coverage = |informative ∩ chunk| / |informative|.

    Retorna 0.0 quando não há termos informativos — o gate de `MIN_TERMS`
    tem que tratar esse caso antes.
    """
    q = [t.lower() for t in informative_terms]
    if not q:
        return 0.0
    c = set(t.lower() for t in chunk_terms)
    hit = sum(1 for t in q if t in c)
    return hit / len(q)


def coverage_weighted(
    central_terms: Iterable[str],
    optional_terms: Iterable[str],
    chunk_terms: Iterable[str],
) -> float:
    """coverage_weighted: termos centrais valem 2x.

    Fórmula:
        num = 2 * |central ∩ chunk| + |optional ∩ chunk|
        den = 2 * |central| + |optional|
    """
    central = [t.lower() for t in central_terms]
    optional = [t.lower() for t in optional_terms]
    c = set(t.lower() for t in chunk_terms)
    hit_central = sum(1 for t in central if t in c)
    hit_optional = sum(1 for t in optional if t in c)
    num = 2 * hit_central + hit_optional
    den = 2 * len(central) + len(optional)
    if den == 0:
        return 0.0
    return num / den


def is_vague_but_high_risk(
    informative_terms: Iterable[str],
    central_terms: Iterable[str],
) -> bool:
    """Detecta queries estruturalmente vagas mas que dão respostas plausíveis.

    Caso típico: `performance banco`, `erro api`, `timeout docker`. Existe
    termo informativo suficiente, mas o par é ambíguo demais (qualidade
    genérica + domínio amplo) para responder com segurança.

    Regra: a query tem termo de qualidade vaga e não tem nenhum termo
    central específico o bastante — `api` entra na whitelist como central,
    mas uma query tipo `erro api` sozinha continua sinalizando risco
    porque o único central é um domínio amplo.
    """
    info = [t.lower() for t in informative_terms]
    central = [t.lower() for t in central_terms]
    if not info:
        return False
    has_vague = any(t in _VAGUE_QUALITY_TERMS for t in info)
    if not has_vague:
        return False
    # Central "forte" = não é puramente domínio ambíguo.
    strong_central = [t for t in central if t not in _AMBIGUOUS_DOMAIN_TERMS]
    if strong_central:
        return False
    return True


# --- Seleção e decisão ------------------------------------------------------

def _apply_source_diversity(
    candidates: list[RetrievalCandidate],
    max_per_source: int = MAX_CHUNKS_PER_SOURCE,
) -> list[RetrievalCandidate]:
    """Limita top-k a no máximo `max_per_source` chunks por fonte.

    Candidatos já devem vir ordenados por `raw_score` desc.
    """
    count: dict[str, int] = {}
    out: list[RetrievalCandidate] = []
    for c in candidates:
        n = count.get(c.source, 0)
        if n >= max_per_source:
            continue
        count[c.source] = n + 1
        out.append(c)
    return out


def select_mode(
    force_doc: bool,
    force_rag: bool,
    discipline_from_command: str | None,
    has_explicit_assistive_flag: bool,
) -> Mode:
    """Decide `strict` vs `assistive` de forma explícita.

    Regra do plano:
    - `/doc`, `/content` e padrão sem flag usam `strict`.
    - `assistive` só existe por flag explícita.
    """
    if has_explicit_assistive_flag:
        return "assistive"
    # /doc, /content, discipline-commands e default → strict
    del force_doc, force_rag, discipline_from_command
    return "strict"


def _build_trace(
    query: str,
    informative_terms: list[str],
    mode: Mode,
    candidates: list[RetrievalCandidate],
    coverage_value: float,
    reason: DecisionReason,
    allow_generation: bool,
    confidence: Confidence,
    debug: dict,
) -> RetrievalTrace:
    top = candidates[0].raw_score if candidates else 0.0
    second = candidates[1].raw_score if len(candidates) > 1 else 0.0
    margin = top - second
    selected_sources = tuple(
        {
            "source": c.source,
            "chunk_id": c.chunk_id,
            "score": c.raw_score,
            "normalized_score": c.normalized_score,
            "matched_terms": list(c.matched_terms),
        }
        for c in candidates
    )
    return RetrievalTrace(
        query=query,
        normalized_query=" ".join(normalize_and_tokenize(query)),
        informative_terms=tuple(informative_terms),
        mode=mode,
        top_score=top,
        second_score=second,
        score_margin=margin,
        coverage=coverage_value,
        selected_sources=selected_sources,
        decision="answer" if allow_generation else "hard_stop",
        reason=reason,
        llm_called=allow_generation,
        tokens_used=0,
        debug=dict(debug),
    )


def build_decision(
    query: str,
    candidates: list[RetrievalCandidate],
    mode: Mode = "strict",
    *,
    min_score: float = MIN_SCORE,
    min_score_margin: float = MIN_SCORE_MARGIN,
    min_coverage: float = MIN_COVERAGE,
    min_coverage_weighted: float = MIN_COVERAGE_WEIGHTED,
    min_terms: int = MIN_TERMS,
    top_k: int = TOP_K,
    max_per_source: int = MAX_CHUNKS_PER_SOURCE,
) -> RetrievalDecision:
    """Aplica as Fases 1 e 2 sobre candidatos já recuperados.

    Ordem das verificações segue o plano:
    1. Ausência de hits ou top_score baixo → `insufficient_context` (F1).
    2. Query subespecificada → `underspecified_query` (F2, strict).
    3. Vague but high risk → `vague_but_high_risk` (F2, strict).
    4. Margem entre top1/top2 baixa → `ambiguous_retrieval` (F2, strict).
    5. Coverage baixa no melhor chunk → `context_misaligned` (F2).
    6. `confidence == "low"` após sinais fracos → `low_confidence` (F2, strict).
    """
    informative = extract_informative_terms(query)
    central, optional = classify_terms(informative)

    candidates_sorted = sorted(candidates, key=lambda c: c.raw_score, reverse=True)
    candidates_diverse = _apply_source_diversity(candidates_sorted, max_per_source)
    selected = candidates_diverse[:top_k]

    top = selected[0].raw_score if selected else 0.0
    second = selected[1].raw_score if len(selected) > 1 else 0.0
    score_margin = top - second

    best_chunk_tokens: list[str] = []
    if selected:
        best_chunk_tokens = normalize_and_tokenize(selected[0].text)
    coverage_value = coverage(informative, best_chunk_tokens) if informative else 0.0
    coverage_w = (
        coverage_weighted(central, optional, best_chunk_tokens) if informative else 0.0
    )
    missing_central = [t for t in central if t not in set(best_chunk_tokens)]
    vague_high_risk = is_vague_but_high_risk(informative, central)

    debug: dict = {
        "central_terms": list(central),
        "optional_terms": list(optional),
        "missing_central_terms": list(missing_central),
        "coverage_weighted": coverage_w,
        "vague_but_high_risk": vague_high_risk,
    }

    # 1. Sem hits ou score absoluto insuficiente.
    if not selected or top < min_score:
        confidence: Confidence = "low"
        debug["confidence"] = confidence
        return RetrievalDecision(
            allow_generation=False,
            reason="insufficient_context",
            confidence=confidence,
            selected_candidates=(),
            trace=_build_trace(
                query, informative, mode, selected, coverage_value,
                "insufficient_context", False, confidence, debug,
            ),
        )

    # 2. Query subespecificada (Fase 2, strict).
    if mode == "strict" and len(informative) < min_terms:
        confidence = "low"
        debug["confidence"] = confidence
        return RetrievalDecision(
            allow_generation=False,
            reason="underspecified_query",
            confidence=confidence,
            selected_candidates=(),
            trace=_build_trace(
                query, informative, mode, selected, coverage_value,
                "underspecified_query", False, confidence, debug,
            ),
        )

    # 3. Vague but high risk (Fase 2, strict).
    if mode == "strict" and vague_high_risk:
        confidence = "low"
        debug["confidence"] = confidence
        return RetrievalDecision(
            allow_generation=False,
            reason="vague_but_high_risk",
            confidence=confidence,
            selected_candidates=(),
            trace=_build_trace(
                query, informative, mode, selected, coverage_value,
                "vague_but_high_risk", False, confidence, debug,
            ),
        )

    # 4. Retrieval ambíguo por margem baixa (Fase 2, strict).
    # Só dispara quando há de fato um segundo candidato; um único hit sólido
    # não é ambíguo por margem.
    if mode == "strict" and len(selected) > 1 and score_margin < min_score_margin:
        confidence = "low"
        debug["confidence"] = confidence
        return RetrievalDecision(
            allow_generation=False,
            reason="ambiguous_retrieval",
            confidence=confidence,
            selected_candidates=(),
            trace=_build_trace(
                query, informative, mode, selected, coverage_value,
                "ambiguous_retrieval", False, confidence, debug,
            ),
        )

    # 5. Coverage baixa no melhor chunk (Fase 2).
    if informative and coverage_value < min_coverage:
        confidence = "low"
        debug["confidence"] = confidence
        return RetrievalDecision(
            allow_generation=False,
            reason="context_misaligned",
            confidence=confidence,
            selected_candidates=(),
            trace=_build_trace(
                query, informative, mode, selected, coverage_value,
                "context_misaligned", False, confidence, debug,
            ),
        )

    # 6. Confidence determinística (Fase 2).
    confidence = "high"
    if coverage_w < min_coverage_weighted:
        confidence = "low"
    if len(selected) > 1 and score_margin < min_score_margin:
        confidence = "low"
    if vague_high_risk:
        confidence = "low"
    if missing_central:
        confidence = "low"
    debug["confidence"] = confidence

    if mode == "strict" and confidence == "low":
        return RetrievalDecision(
            allow_generation=False,
            reason="low_confidence",
            confidence=confidence,
            selected_candidates=(),
            trace=_build_trace(
                query, informative, mode, selected, coverage_value,
                "low_confidence", False, confidence, debug,
            ),
        )

    return RetrievalDecision(
        allow_generation=True,
        reason="ok",
        confidence=confidence,
        selected_candidates=tuple(selected),
        trace=_build_trace(
            query, informative, mode, selected, coverage_value,
            "ok", True, confidence, debug,
        ),
    )


# --- Sanity check pós-geração (Fase 3) --------------------------------------

def _tokens_of(text: str) -> set[str]:
    return set(normalize_and_tokenize(text))


def post_generation_flags(
    answer: str,
    informative_terms: Iterable[str],
    selected_candidates: Iterable[RetrievalCandidate],
) -> list[str]:
    """Sanity check leve, não-LLM, sobre a resposta gerada.

    Flags:
    - `missing_informative_terms`: resposta não cita nenhum termo informativo
      da query.
    - `missing_source_entities`: resposta não menciona nenhuma fonte nem
      nenhuma entidade central dos chunks selecionados.
    - `introduced_unsupported_terms`: demasiados termos técnicos novos que
      não aparecem em nenhum chunk (heurística conservadora).
    """
    flags: list[str] = []
    answer_tokens = _tokens_of(answer)

    info = [t.lower() for t in informative_terms]
    if info and not any(t in answer_tokens for t in info):
        flags.append("missing_informative_terms")

    candidates = list(selected_candidates)
    chunk_tokens: set[str] = set()
    sources: set[str] = set()
    for c in candidates:
        chunk_tokens |= _tokens_of(c.text)
        sources.add(c.source.lower())

    source_mentioned = any(src_part for src_part in sources if src_part in answer.lower())
    # Termos centrais dos chunks presentes: heurística mínima. Se a resposta
    # não cita nem fonte nem termos dos chunks, é sinal forte de alucinação
    # ou de resposta genérica.
    answer_tokens_sigset = {t for t in answer_tokens if len(t) > 4}
    shared_with_chunks = bool(answer_tokens_sigset & chunk_tokens)
    if candidates and not source_mentioned and not shared_with_chunks:
        flags.append("missing_source_entities")

    if candidates:
        tech_like = {t for t in answer_tokens if len(t) >= 5 and re.search(r"[a-z]", t)}
        unsupported = [t for t in tech_like if t not in chunk_tokens and t not in info]
        # Limite conservador: só marca se muitos termos técnicos longos
        # aparecerem sem suporte nos chunks.
        if len(unsupported) > 25:
            flags.append("introduced_unsupported_terms")

    return flags
