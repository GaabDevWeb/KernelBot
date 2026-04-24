# Para rodar: 

#python scripts\run_questions.py `
# --questions questions.md `
# --base-url http://127.0.0.1:8001 `
# --out evaluation\questions_answers.json `
# --resume `
# --batch-size 10

from __future__ import annotations

from pathlib import Path

# Ensure the scripts package is importable
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_questions import parse_questions_md


def test_parse_questions_md_ignores_titles_and_parses_lines(tmp_path: Path):
    p = tmp_path / "questions.md"
    p.write_text(
        "\n".join(
            [
                "🔹 /python (1–50)",
                "/python o que é uma variável em python",
                "/visualizacao-sql o que é select",
                "   ",
                "🤮 Perguntas mal escritas / usuário real (241–270)",
                "/python como faz variavel msm",
                "/invalid-line-sem-espaco",
                "/python    com   espaços   extras   ",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    items = parse_questions_md(p)
    assert [(i.discipline, i.question) for i in items] == [
        ("python", "o que é uma variável em python"),
        ("visualizacao-sql", "o que é select"),
        ("python", "como faz variavel msm"),
        ("python", "com   espaços   extras"),
    ]

