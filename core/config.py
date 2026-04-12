"""Configuração tipada carregada do ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

GlobalContextMode = Literal["geral", "all"]


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
            "arcee-ai/trinity-large-preview:free",
            "google/gemini-2.5-flash:free",
            "meta-llama/llama-3.3-70b-instruct:free",
        )
        system_prompt = (
            "Você é o ACL (Agente de Contexto Local), um assistente técnico direto e preciso. "
            "Responda em português (PT-BR). Evite enrolação."
        )

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

        """ !Credenciais do banco! """

        db_host = (os.getenv("DB_HOST") or "").strip()

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
            http_timeout=60.0,
            pinned_max_turns=pinned_max_turns,
            pinned_max_chars=pinned_max_chars,
            pinned_weak_score=pinned_weak_score,
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
        )
