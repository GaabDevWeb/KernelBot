"""Contexto institucional — informações estáveis da faculdade/turma.

Lê ficheiros Markdown de `KERNEL_CONTEXT_DIR` (default `context/`):
`identity.md`, `faculty.md`, `professors.md`, `disciplines.md`, `rules.md`.

Ficheiros ausentes, vazios ou contendo apenas comentários HTML (placeholders
do template) são ignorados — nunca entram no prompt como facto. O template
para preenchimento humano é `context/context.md` (não é carregado).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from pathlib import Path

log = logging.getLogger(f"kernelbots.{__name__}")

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# (ficheiro, título da secção no prompt) — ordem de injeção.
SECTION_FILES: tuple[tuple[str, str], ...] = (
    ("identity.md", "Identidade do assistente"),
    ("faculty.md", "Instituição"),
    ("professors.md", "Professores"),
    ("disciplines.md", "Disciplinas"),
    ("rules.md", "Regras da instituição/turma"),
)


def _clean_content(raw: str) -> str:
    """Remove comentários HTML (instruções de preenchimento) e espaços."""
    return _HTML_COMMENT_RE.sub("", raw).strip()


class InstitutionalContextProvider:
    """Concatena as secções institucionais preenchidas pelo operador."""

    def __init__(self, context_dir: Path | str | None) -> None:
        self._dir = Path(context_dir) if context_dir else None

    def _read_section(self, filename: str) -> str:
        if self._dir is None:
            return ""
        path = self._dir / filename
        if not path.is_file():
            return ""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("institutional: falha ao ler %s (%s)", path, exc)
            return ""
        return _clean_content(raw)

    def load_sections(
        self, *, files: Sequence[str] | None = None
    ) -> tuple[tuple[str, str, str], ...]:
        """(filename, título, conteúdo) apenas das secções com conteúdo real.

        `files is None` → todos os SECTION_FILES (legado).
        `files` lista/tuplo → só esses basenames, na ordem canónica.
        Lista vazia → nenhuma secção.
        """
        if files is not None:
            allow = {str(f).strip() for f in files if str(f).strip()}
            if not allow:
                return ()
            wanted = tuple(
                (filename, title)
                for filename, title in SECTION_FILES
                if filename in allow
            )
        else:
            wanted = SECTION_FILES

        out: list[tuple[str, str, str]] = []
        for filename, title in wanted:
            content = self._read_section(filename)
            if content:
                out.append((filename, title, content))
        return tuple(out)

    def prompt_block(
        self, *, files: Sequence[str] | None = None
    ) -> tuple[str, tuple[str, ...]]:
        """(bloco de prompt, ficheiros usados). Vazio se nada preenchido.

        `files is None` → todos (legado). `files` → allowlist de basenames.
        """
        sections = self.load_sections(files=files)
        if not sections:
            return "", ()
        parts = ["## Contexto institucional (fonte oficial da turma/faculdade)"]
        for _filename, title, content in sections:
            parts.append(f"### {title}\n\n{content}")
        parts.append(
            "As informações acima foram fornecidas pelo responsável da turma e "
            "são fonte oficial. Não contradiga estes dados com conhecimento "
            "geral; se algo não constar aqui nem nas outras fontes, declare a "
            "ausência."
        )
        return "\n\n".join(parts), tuple(s[0] for s in sections)
