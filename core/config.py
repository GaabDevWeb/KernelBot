"""Configuração tipada carregada do ambiente."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

GlobalContextMode = Literal["geral", "all"]

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
    openrouter_api_key: str
    project_root: Path
    content_dir: Path
    bm25_score_threshold: float
    global_context_mode: GlobalContextMode
    openrouter_base: str
    models: tuple[str, ...]
    system_prompt_geral: str
    sticky_instruction: str
    http_timeout: float
    # Contexto fixado (sessão): ver `documentation.md`
    pinned_max_turns: int
    pinned_max_chars: int
    pinned_weak_score: float
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

    @property
    def openrouter_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "ACL - Agente de Contexto Local",
        }

    @classmethod
    def load(cls) -> Settings:
        load_dotenv()
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY ausente no .env — impossível iniciar.")

        project_root = Path(__file__).resolve().parent.parent
        content_dir = project_root / "content"
        content_dir.mkdir(exist_ok=True)

        models = (
            "openrouter/free",
            "deepseek/deepseek-r1:free",
            "meta-llama/llama-4-maverick:free",
        )

        prompts_dir = Path(__file__).resolve().parent / "systemPrompt"
        system_prompt_file = prompts_dir / "system_prompt.txt"
        sticky_instruction_file = prompts_dir / "sticky_instruction.txt"

        if not system_prompt_file.exists():
            raise RuntimeError(
                f"Arquivo de system prompt não encontrado: {system_prompt_file}. "
                "Crie o arquivo core/systemPrompt/system_prompt.txt com o texto do assistente."
            )
        if not sticky_instruction_file.exists():
            raise RuntimeError(
                f"Arquivo de instrução sticky não encontrado: {sticky_instruction_file}. "
                "Crie o arquivo core/systemPrompt/sticky_instruction.txt com o template de contexto fixado."
            )

        system_prompt = system_prompt_file.read_text(encoding="utf-8").strip()
        sticky_instruction = sticky_instruction_file.read_text(encoding="utf-8").strip()

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
            openrouter_api_key=key,
            project_root=project_root,
            content_dir=content_dir,
            bm25_score_threshold=0.7,
            global_context_mode=global_context_mode,
            openrouter_base="https://openrouter.ai/api/v1/chat/completions",
            models=models,
            system_prompt_geral=system_prompt,
            sticky_instruction=sticky_instruction,
            http_timeout=60.0,
            pinned_max_turns=pinned_max_turns,
            pinned_max_chars=pinned_max_chars,
            pinned_weak_score=pinned_weak_score,
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
        )
