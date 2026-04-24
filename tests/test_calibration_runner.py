"""Testes do gerador de traces de calibração."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.calibration_runner import _mode_for, parse_questions


def test_parse_questions_extracts_command_and_query(tmp_path: Path):
    p = tmp_path / "q.md"
    p.write_text(
        "\n".join(
            [
                "# Título ignorado",
                "",
                "/python como usar variavel",
                "/doc como funciona /reload",
                "/content performance",
                "/visualizacao-sql sql select from",
                "emoji-only-linha-sem-comando",
                "/sem-espaco-no-comando",
            ]
        ),
        encoding="utf-8",
    )

    items = parse_questions(p)
    # /doc vira discipline="doc"; /content vira discipline=None; /xyz vira "xyz".
    assert items == [
        ("python", "como usar variavel", "/python como usar variavel"),
        ("doc", "como funciona /reload", "/doc como funciona /reload"),
        (None, "performance", "/content performance"),
        ("visualizacao-sql", "sql select from", "/visualizacao-sql sql select from"),
    ]


def test_mode_for_is_always_strict_for_each_command():
    assert _mode_for("python") == "strict"
    assert _mode_for("doc") == "strict"
    assert _mode_for(None) == "strict"
    assert _mode_for("visualizacao-sql") == "strict"
