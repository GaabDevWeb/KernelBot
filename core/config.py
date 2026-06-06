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

        if llm_provider == "openrouter" and not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY ausente no .env — impossível iniciar (provider=openrouter).")
        if llm_provider == "cursor" and not cursor_key:
            raise RuntimeError("CURSOR_API_KEY ausente no .env — impossível iniciar (provider=cursor).")

        project_root = Path(__file__).resolve().parent.parent
        content_dir = project_root / "content"
        content_dir.mkdir(exist_ok=True)

        models = (
            "deepseek/deepseek-v4-flash:free ",
            "openrouter/free",
            "meta-llama/llama-4-maverick:free",
        )

        prompts_dir = Path(__file__).resolve().parent / "systemPrompt"
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
                "Crie o arquivo core/systemPrompt/system_prompt.txt com o texto do assistente."
            )
        if not grounding_strict_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding não encontrado: {grounding_strict_file}. "
                "Crie o arquivo core/systemPrompt/grounding_strict.txt com o contrato anti-alucinação."
            )
        if not grounding_anchored_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding anchored não encontrado: {grounding_anchored_file}. "
                "Crie o arquivo core/systemPrompt/grounding_anchored.txt."
            )
        if not grounding_permissive_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding permissivo não encontrado: {grounding_permissive_file}. "
                "Crie o arquivo core/systemPrompt/grounding_permissive.txt."
            )
        if not grounding_disambiguation_file.exists():
            raise RuntimeError(
                f"Arquivo de grounding de desambiguação não encontrado: {grounding_disambiguation_file}. "
                "Crie o arquivo core/systemPrompt/grounding_disambiguation.txt."
            )
        if not sticky_instruction_file.exists():
            raise RuntimeError(
                f"Arquivo de instrução sticky não encontrado: {sticky_instruction_file}. "
                "Crie o arquivo core/systemPrompt/sticky_instruction.txt com o template de contexto fixado."
            )
        if not catalog_router_file.exists():
            raise RuntimeError(
                f"Arquivo de prompt do catálogo não encontrado: {catalog_router_file}. "
                "Crie o arquivo core/systemPrompt/catalog_router.txt com as instruções de contexto do catálogo."
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

        return cls(
            llm_provider=llm_provider,
            openrouter_api_key=openrouter_key,
            cursor_api_key=cursor_key,
            cursor_model=cursor_model,
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
        )
