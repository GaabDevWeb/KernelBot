"""Configuração tipada carregada do ambiente."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

GlobalContextMode = Literal["geral", "all"]
RetrievalPolicyMode = Literal["strict", "fallback"]
LLMProvider = Literal["openrouter", "cursor"]
GroundingPolicy = Literal["strict", "anchored", "hybrid"]

_LOG = logging.getLogger("kernelbots.config")


def _normalize_db_host(raw: str) -> str:
    """127.0.0.0 é typo frequente; o loopback usual é 127.0.0.1."""
    h = (raw or "").strip().strip("'\"")
    if h == "127.0.0.0":
        _LOG.warning(
            "DB_HOST era '127.0.0.0'; a usar '127.0.0.1'. Corrija o .env para evitar este aviso."
        )
        return "127.0.0.1"
    return h


@dataclass(frozen=True)
class Settings:
    llm_provider: LLMProvider
    openrouter_api_key: str
    cursor_api_key: str
    cursor_model: str
    cursor_chat_only: bool
    project_root: Path
    content_dir: Path
    bm25_score_threshold: float
    global_context_mode: GlobalContextMode
    openrouter_base: str
    models: tuple[str, ...]
    system_prompt_geral: str
    grounding_policy: GroundingPolicy
    grounding_strict: str
    grounding_anchored: str
    grounding_permissive: str
    grounding_disambiguation: str
    sticky_instruction: str
    retrieval_mode: RetrievalPolicyMode
    disambiguation_enabled: bool
    http_timeout: float
    # Contexto fixado (sessão): ver `documentation.md`
    pinned_max_turns: int
    pinned_max_chars: int
    pinned_weak_score: float
    # Histórico de diálogo no prompt (POC — não indexa no RAG)
    chat_history_max_turns: int
    chat_history_max_chars: int
    # Transcript store v1 (Kernel↔Orbit): ver kernel/memory/transcript_store.py
    transcript_max_turns: int
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    # Thresholds da política de retrieval (ver engine/retrieval.py e o plano
    # rag_acl_incremental). Todos devem ser recalibrados com amostra manual
    # antes de serem tratados como definitivos.
    retrieval_min_score: float
    retrieval_min_score_margin: float
    retrieval_min_coverage: float
    retrieval_min_coverage_weighted: float
    retrieval_min_terms: int
    retrieval_candidate_k: int
    retrieval_top_k: int
    retrieval_max_chunks_per_source: int
    # Catálogo lexical de aulas (ISS JSON) — ver engine/lesson_catalog.py
    catalog_enabled: bool
    catalog_json_dir: Path | None
    catalog_min_score: float
    catalog_min_margin: float
    # Limiar alto para pré-escopo BM25 (Fase futura); não relaxar retrieval BM25.
    catalog_strict_threshold: float
    catalog_prompt_top_k: int
    catalog_router_prompt: str
    # Token Bearer para /reload e GET /health/catalog (CI, operadores).
    reload_bearer_token: str | None
    # URL pública da aula no ISS (frontend — links de fonte).
    iss_public_lesson_base: str
    # TRACE operacional (SQLite + painel /traces) — ADR-0003 / Flight Recorder.
    trace_db_path: Path
    trace_retention_days: int
    # Contexto em camadas (identity/institucional/temporal/calendar) — ver
    # docs/CONTEXT-ARCHITECTURE.md. Defaults preservam compat com testes que
    # constroem Settings directamente.
    kernel_timezone: str = "America/Sao_Paulo"
    context_dir: Path | None = None
    calendar_path: Path | None = None
    identity_prompt: str = ""
    # ContextRouter FAST|NORMAL|DEEP — default off = camadas always-on (legado).
    context_router_enabled: bool = False
    # Memória Histórica de Grupos (SQLite + BM25 + Recência)
    group_memory_db_path: Path | None = None
    group_memory_enabled: bool = True
    group_memory_max_results: int = 5
    group_memory_recency_weight: float = 0.3
    group_memory_max_chars: int = 4000
    group_memory_retention_days: int = 0
    group_profile_enabled: bool = True
    group_profile_update_threshold: int = 50
    idempotency_enabled: bool = True
    idempotency_ttl_seconds: int = 300

    @property
    def openrouter_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Kernel - Assistente de Estudo",
        }

    @classmethod
    def load(cls) -> Settings:
        project_root = Path(__file__).resolve().parent.parent
        staging_env = project_root / ".env.staging.local"
        if os.getenv("KERNELBOT_ENV", "").strip().lower() == "staging" and staging_env.is_file():
            load_dotenv(staging_env, override=True)
        load_dotenv()
        if os.getenv("KERNELBOT_ENV", "").strip().lower() == "staging" and staging_env.is_file():
            load_dotenv(staging_env, override=True)
        raw_provider = (os.getenv("ACL_LLM_PROVIDER") or "cursor").strip().lower()
        if raw_provider not in ("openrouter", "cursor"):
            raise RuntimeError(
                "ACL_LLM_PROVIDER deve ser 'openrouter' ou 'cursor' "
                f"(recebido: {raw_provider!r})."
            )
        llm_provider: LLMProvider = "cursor" if raw_provider == "cursor" else "openrouter"

        openrouter_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        cursor_key = (os.getenv("CURSOR_API_KEY") or "").strip()
        cursor_model = (os.getenv("ACL_CURSOR_MODEL") or "composer-2.5").strip()
        # Default seguro: chat-only (workspace vazio). Opt-out explícito com false.
        _cursor_chat_raw = (os.getenv("ACL_CURSOR_CHAT_ONLY") or "").strip().lower()
        if not _cursor_chat_raw:
            cursor_chat_only = True
        else:
            cursor_chat_only = _cursor_chat_raw in ("1", "true", "yes", "on")

        if llm_provider == "openrouter" and not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY ausente no .env — impossível iniciar (provider=openrouter).")
        if llm_provider == "cursor" and not cursor_key:
            raise RuntimeError("CURSOR_API_KEY ausente no .env — impossível iniciar (provider=cursor).")

        project_root = Path(__file__).resolve().parent.parent
        content_dir = project_root / "content"
        content_dir.mkdir(exist_ok=True)

        models = (
            "openrouter/free",
            "deepseek/deepseek-v4-flash",
            "meta-llama/llama-4-maverick",
        )

        prompts_dir = Path(__file__).resolve().parent / "policies" / "systemPrompt"
        system_prompt_file = prompts_dir / "system_prompt.txt"
        grounding_strict_file = prompts_dir / "grounding_strict.txt"
        grounding_anchored_file = prompts_dir / "grounding_anchored.txt"
        grounding_permissive_file = prompts_dir / "grounding_permissive.txt"
        grounding_disambiguation_file = prompts_dir / "grounding_disambiguation.txt"
        sticky_instruction_file = prompts_dir / "sticky_instruction.txt"
        catalog_router_file = prompts_dir / "catalog_router.txt"

        if not system_prompt_file.exists():
            raise RuntimeError(
                f"Arquivo de system prompt não encontrado: {system_prompt_file}. "
                "Crie o arquivo kernel/policies/systemPrompt/system_prompt.txt com o texto do assistente."
            )
        if not grounding_strict_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding não encontrado: {grounding_strict_file}. "
                "Crie o arquivo kernel/policies/systemPrompt/grounding_strict.txt com o contrato anti-alucinação."
            )
        if not grounding_anchored_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding anchored não encontrado: {grounding_anchored_file}. "
                "Crie o arquivo kernel/policies/systemPrompt/grounding_anchored.txt."
            )
        if not grounding_permissive_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding permissivo não encontrado: {grounding_permissive_file}. "
                "Crie o arquivo kernel/policies/systemPrompt/grounding_permissive.txt."
            )
        if not grounding_disambiguation_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding de desambiguação não encontrado: {grounding_disambiguation_file}. "
                "Crie o arquivo kernel/policies/systemPrompt/grounding_disambiguation.txt."
            )
        if not sticky_instruction_file.exists():
            raise RuntimeError(
                f"Arquivo de instrução sticky não encontrado: {sticky_instruction_file}. "
                "Crie o arquivo kernel/policies/systemPrompt/sticky_instruction.txt com o template de contexto fixado."
            )
        if not catalog_router_file.exists():
            raise RuntimeError(
                f"Arquivo de prompt do catálogo não encontrado: {catalog_router_file}. "
                "Crie o arquivo kernel/policies/systemPrompt/catalog_router.txt com as instruções de contexto do catálogo."
            )

        system_prompt = system_prompt_file.read_text(encoding="utf-8").strip()
        raw_grounding_policy = (os.getenv("ACL_GROUNDING_POLICY") or "anchored").strip().lower()
        if raw_grounding_policy not in ("strict", "anchored", "hybrid"):
            raise RuntimeError(
                "ACL_GROUNDING_POLICY deve ser 'strict', 'anchored' ou 'hybrid' "
                f"(recebido: {raw_grounding_policy!r})."
            )
        grounding_policy: GroundingPolicy = raw_grounding_policy  # type: ignore[assignment]

        grounding_strict = grounding_strict_file.read_text(encoding="utf-8").strip()
        grounding_anchored = grounding_anchored_file.read_text(encoding="utf-8").strip()
        grounding_permissive = grounding_permissive_file.read_text(encoding="utf-8").strip()
        grounding_disambiguation = grounding_disambiguation_file.read_text(encoding="utf-8").strip()
        sticky_instruction = sticky_instruction_file.read_text(encoding="utf-8").strip()
        catalog_router_prompt = catalog_router_file.read_text(encoding="utf-8").strip()

        raw_global = (os.getenv("ACL_GLOBAL_CONTEXT") or "geral").strip().lower()
        if raw_global == "geral":
            global_context_mode: GlobalContextMode = "geral"
        elif raw_global == "all":
            global_context_mode = "all"
        else:
            raise RuntimeError(
                "ACL_GLOBAL_CONTEXT deve ser 'geral' ou 'all' "
                f"(recebido: {raw_global!r})."
            )

        try:
            pinned_max_turns = int((os.getenv("ACL_PINNED_MAX_TURNS") or "5").strip())
        except ValueError:
            raise RuntimeError("ACL_PINNED_MAX_TURNS deve ser um inteiro.") from None
        pinned_max_turns = max(1, min(50, pinned_max_turns))

        try:
            pinned_max_chars = int((os.getenv("ACL_PINNED_MAX_CHARS") or "24000").strip())
        except ValueError:
            raise RuntimeError("ACL_PINNED_MAX_CHARS deve ser um inteiro.") from None
        pinned_max_chars = max(2000, min(200_000, pinned_max_chars))

        try:
            pinned_weak_score = float((os.getenv("ACL_PINNED_WEAK_SCORE") or "0.4").strip())
        except ValueError:
            raise RuntimeError("ACL_PINNED_WEAK_SCORE deve ser um número.") from None
        pinned_weak_score = max(0.05, min(0.95, pinned_weak_score))

        def _env_float(name: str, default: float, lo: float, hi: float) -> float:
            raw = (os.getenv(name) or str(default)).strip()
            try:
                v = float(raw)
            except ValueError:
                raise RuntimeError(f"{name} deve ser um número.") from None
            return max(lo, min(hi, v))

        def _env_int(name: str, default: int, lo: int, hi: int) -> int:
            raw = (os.getenv(name) or str(default)).strip()
            try:
                v = int(raw)
            except ValueError:
                raise RuntimeError(f"{name} deve ser um inteiro.") from None
            return max(lo, min(hi, v))

        retrieval_min_score = _env_float("ACL_RETRIEVAL_MIN_SCORE", 1.5, 0.0, 50.0)
        retrieval_min_score_margin = _env_float("ACL_RETRIEVAL_MIN_SCORE_MARGIN", 0.15, 0.0, 5.0)
        retrieval_min_coverage = _env_float("ACL_RETRIEVAL_MIN_COVERAGE", 0.34, 0.0, 1.0)
        retrieval_min_coverage_weighted = _env_float(
            "ACL_RETRIEVAL_MIN_COVERAGE_WEIGHTED", 0.34, 0.0, 1.0
        )
        retrieval_min_terms = _env_int("ACL_RETRIEVAL_MIN_TERMS", 2, 1, 10)
        retrieval_candidate_k = _env_int("ACL_RETRIEVAL_CANDIDATE_K", 8, 1, 50)
        retrieval_top_k = _env_int("ACL_RETRIEVAL_TOP_K", 4, 1, 20)
        retrieval_max_chunks_per_source = _env_int(
            "ACL_RETRIEVAL_MAX_CHUNKS_PER_SOURCE", 2, 1, 10
        )

        chat_history_max_turns = _env_int("ACL_CHAT_HISTORY_MAX_TURNS", 12, 0, 40)
        chat_history_max_chars = _env_int("ACL_CHAT_HISTORY_MAX_CHARS", 12000, 0, 200_000)
        transcript_max_turns = _env_int("ACL_TRANSCRIPT_MAX_TURNS", 16, 1, 100)
        raw_context_router = (os.getenv("ACL_CONTEXT_ROUTER") or "").strip().lower()
        context_router_enabled = raw_context_router in {"1", "true", "yes", "on"}

        raw_retrieval_mode = (os.getenv("ACL_RETRIEVAL_MODE") or "strict").strip().lower()
        if raw_retrieval_mode not in ("strict", "fallback"):
            raise RuntimeError(
                "ACL_RETRIEVAL_MODE deve ser 'strict' ou 'fallback' (legado) "
                f"(recebido: {raw_retrieval_mode!r})."
            )
        if raw_retrieval_mode == "fallback":
            import logging

            logging.getLogger("kernelbots.config").warning(
                "ACL_RETRIEVAL_MODE=fallback ignorado; gates são só classificação — sempre LLM + grounding_strict"
            )
        retrieval_mode: RetrievalPolicyMode = "strict"

        raw_disambiguation = (os.getenv("ACL_DISAMBIGUATION_ENABLED") or "false").strip().lower()
        disambiguation_enabled = raw_disambiguation in ("1", "true", "yes", "on")

        raw_catalog_enabled = (os.getenv("ACL_CATALOG_ENABLED") or "false").strip().lower()
        catalog_enabled = raw_catalog_enabled in ("1", "true", "yes", "on")

        catalog_json_dir: Path | None = None
        raw_catalog_dir = (os.getenv("ACL_CATALOG_JSON_DIR") or "").strip()
        if raw_catalog_dir:
            raw_path = Path(raw_catalog_dir).expanduser()
            catalog_json_dir = (
                raw_path.resolve()
                if raw_path.is_absolute()
                else (project_root / raw_path).resolve()
            )
        else:
            iss_fallback = project_root.parent / "ISS" / "content"
            if iss_fallback.is_dir():
                catalog_json_dir = iss_fallback.resolve()

        catalog_min_score = _env_float("ACL_CATALOG_MIN_SCORE", 2.0, 0.0, 100.0)
        catalog_min_margin = _env_float("ACL_CATALOG_MIN_MARGIN", 0.35, 0.0, 50.0)
        catalog_strict_threshold = _env_float(
            "ACL_CATALOG_STRICT_THRESHOLD", 4.0, 0.0, 100.0
        )
        catalog_prompt_top_k = _env_int("ACL_CATALOG_PROMPT_TOP_K", 5, 1, 20)

        reload_bearer_token = (
            (os.getenv("ACL_RELOAD_BEARER_TOKEN") or os.getenv("KERNELBOT_RELOAD_TOKEN") or "")
            .strip()
            or None
        )

        iss_public_lesson_base = (
            os.getenv("KERNELBOT_ISS_PUBLIC_BASE_URL") or ""
        ).strip().rstrip("?") or "https://gaabdevweb.github.io/ISS/public/aula.html"

        """ !Credenciais do banco! """

        db_host = _normalize_db_host(os.getenv("DB_HOST") or "")

        db_port_raw = (os.getenv("DB_PORT") or "3306").strip()

        try:
            db_port = int(db_port_raw)
        except ValueError:
            raise RuntimeError("DB_PORT deve ser um inteiro.") from None

        db_name = (os.getenv("DB_NAME") or "").strip()

        db_user = (os.getenv("DB_USER") or "").strip()

        db_password = (os.getenv("DB_PASSWORD") or "").strip()

        raw_trace_db = (os.getenv("ACL_TRACE_DB_PATH") or "data/traces.sqlite3").strip()
        raw_trace_path = Path(raw_trace_db).expanduser()
        trace_db_path = (
            raw_trace_path.resolve()
            if raw_trace_path.is_absolute()
            else (project_root / raw_trace_path).resolve()
        )
        # Garantir que o directório existe (não cria o ficheiro SQLite aqui).
        trace_db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            trace_retention_days = int((os.getenv("ACL_TRACE_RETENTION_DAYS") or "30").strip())
        except ValueError:
            raise RuntimeError("ACL_TRACE_RETENTION_DAYS deve ser um inteiro.") from None
        if trace_retention_days < 1:
            raise RuntimeError("ACL_TRACE_RETENTION_DAYS deve ser >= 1.")

        # --- Contexto em camadas (temporal / institucional / calendar) ------

        kernel_timezone = (os.getenv("KERNEL_TIMEZONE") or "America/Sao_Paulo").strip()
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(kernel_timezone)
        except Exception:
            raise RuntimeError(
                f"KERNEL_TIMEZONE inválido: {kernel_timezone!r}. "
                "Use um identificador IANA, ex.: America/Sao_Paulo."
            ) from None

        raw_context_dir = (os.getenv("KERNEL_CONTEXT_DIR") or "").strip()
        if raw_context_dir:
            ctx_path = Path(raw_context_dir).expanduser()
            context_dir = (
                ctx_path.resolve()
                if ctx_path.is_absolute()
                else (project_root / ctx_path).resolve()
            )
        else:
            context_dir = (project_root / "context").resolve()

        raw_calendar = (os.getenv("KERNEL_CALENDAR_PATH") or "").strip()
        if raw_calendar:
            cal_path = Path(raw_calendar).expanduser()
            calendar_path = (
                cal_path.resolve()
                if cal_path.is_absolute()
                else (project_root / cal_path).resolve()
            )
        else:
            calendar_path = context_dir / "calendar.json"

        # Identidade (camada Orbit): fail-soft — sem o ficheiro, o Kernel
        # arranca com o comportamento anterior (bloco omitido).
        identity_file = prompts_dir / "identity.txt"
        identity_prompt = ""
        if identity_file.exists():
            identity_prompt = identity_file.read_text(encoding="utf-8").strip()
        else:
            _LOG.warning(
                "identity.txt ausente em %s — camada de identidade desativada.",
                prompts_dir,
            )

        raw_group_mem_db = (os.getenv("KERNEL_GROUP_MEMORY_DB_PATH") or "data/group_memory.sqlite3").strip()
        raw_group_mem_path = Path(raw_group_mem_db).expanduser()
        group_memory_db_path = (
            raw_group_mem_path.resolve()
            if raw_group_mem_path.is_absolute()
            else (project_root / raw_group_mem_path).resolve()
        )
        group_memory_db_path.parent.mkdir(parents=True, exist_ok=True)

        group_memory_enabled = (os.getenv("KERNEL_GROUP_MEMORY_ENABLED") or "true").strip().lower() in ("1", "true", "yes", "on")
        group_memory_max_results = _env_int("KERNEL_GROUP_MEMORY_MAX_RESULTS", 5, 1, 20)
        group_memory_recency_weight = _env_float("KERNEL_GROUP_MEMORY_RECENCY_WEIGHT", 0.3, 0.0, 2.0)
        group_memory_max_chars = _env_int("KERNEL_GROUP_MEMORY_MAX_CHARS", 4000, 500, 20000)
        group_memory_retention_days = _env_int("KERNEL_GROUP_MEMORY_RETENTION_DAYS", 0, 0, 3650)

        group_profile_enabled = (os.getenv("KERNEL_GROUP_PROFILE_ENABLED") or "true").strip().lower() in ("1", "true", "yes", "on")
        group_profile_update_threshold = _env_int("KERNEL_GROUP_PROFILE_UPDATE_THRESHOLD", 50, 5, 500)

        idempotency_enabled = (os.getenv("KERNEL_IDEMPOTENCY_ENABLED") or "true").strip().lower() in ("1", "true", "yes", "on")
        idempotency_ttl_seconds = _env_int("KERNEL_IDEMPOTENCY_TTL_SECONDS", 300, 10, 86400)

        return cls(
            llm_provider=llm_provider,
            openrouter_api_key=openrouter_key,
            cursor_api_key=cursor_key,
            cursor_model=cursor_model,
            cursor_chat_only=cursor_chat_only,
            project_root=project_root,
            content_dir=content_dir,
            bm25_score_threshold=0.7,
            global_context_mode=global_context_mode,
            openrouter_base="https://openrouter.ai/api/v1/chat/completions",
            models=models,
            system_prompt_geral=system_prompt,
            grounding_policy=grounding_policy,
            grounding_strict=grounding_strict,
            grounding_anchored=grounding_anchored,
            grounding_permissive=grounding_permissive,
            grounding_disambiguation=grounding_disambiguation,
            sticky_instruction=sticky_instruction,
            retrieval_mode=retrieval_mode,
            disambiguation_enabled=disambiguation_enabled,
            http_timeout=60.0,
            pinned_max_turns=pinned_max_turns,
            pinned_max_chars=pinned_max_chars,
            pinned_weak_score=pinned_weak_score,
            chat_history_max_turns=chat_history_max_turns,
            chat_history_max_chars=chat_history_max_chars,
            transcript_max_turns=transcript_max_turns,
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            retrieval_min_score=retrieval_min_score,
            retrieval_min_score_margin=retrieval_min_score_margin,
            retrieval_min_coverage=retrieval_min_coverage,
            retrieval_min_coverage_weighted=retrieval_min_coverage_weighted,
            retrieval_min_terms=retrieval_min_terms,
            retrieval_candidate_k=retrieval_candidate_k,
            retrieval_top_k=retrieval_top_k,
            retrieval_max_chunks_per_source=retrieval_max_chunks_per_source,
            catalog_enabled=catalog_enabled,
            catalog_json_dir=catalog_json_dir,
            catalog_min_score=catalog_min_score,
            catalog_min_margin=catalog_min_margin,
            catalog_strict_threshold=catalog_strict_threshold,
            catalog_prompt_top_k=catalog_prompt_top_k,
            catalog_router_prompt=catalog_router_prompt,
            reload_bearer_token=reload_bearer_token,
            iss_public_lesson_base=iss_public_lesson_base,
            trace_db_path=trace_db_path,
            trace_retention_days=trace_retention_days,
            kernel_timezone=kernel_timezone,
            context_dir=context_dir,
            calendar_path=calendar_path,
            identity_prompt=identity_prompt,
            context_router_enabled=context_router_enabled,
            group_memory_db_path=group_memory_db_path,
            group_memory_enabled=group_memory_enabled,
            group_memory_max_results=group_memory_max_results,
            group_memory_recency_weight=group_memory_recency_weight,
            group_memory_max_chars=group_memory_max_chars,
            group_memory_retention_days=group_memory_retention_days,
            group_profile_enabled=group_profile_enabled,
            group_profile_update_threshold=group_profile_update_threshold,
            idempotency_enabled=idempotency_enabled,
            idempotency_ttl_seconds=idempotency_ttl_seconds,
        )
