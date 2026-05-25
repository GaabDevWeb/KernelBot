"""Testes do parser de `<ambiguity_options>` / JSON de desambiguação."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.disambiguation_parse import (
    parse_ambiguity_options,
    parse_incomplete_ambiguity_options,
    strip_ambiguity_markup,
)


class TestDisambiguationParse(unittest.TestCase):
    def test_xml_options(self) -> None:
        text = """Intro breve.
<ambiguity_options>
<option discipline="python" slug="python__01" label="Por que programar"/>
<option discipline="python" slug="python__02" label="Algoritmos"/>
</ambiguity_options>"""
        opts = parse_ambiguity_options(text)
        self.assertEqual(len(opts), 2)
        self.assertEqual(opts[0]["discipline"], "python")
        self.assertEqual(opts[0]["slug"], "python__01")
        self.assertEqual(opts[0]["title"], "Por que programar")

    def test_json_options(self) -> None:
        text = (
            '{"disambiguation_options":[{"discipline":"sql","slug":"aula-1",'
            '"label":"Modelagem"}]}'
        )
        opts = parse_ambiguity_options(text)
        self.assertEqual(len(opts), 1)
        self.assertEqual(opts[0]["discipline"], "sql")

    def test_strip_removes_markup(self) -> None:
        raw = (
            "Não consigo escolher.\n"
            '<ambiguity_options><option discipline="a" slug="b" label="C"/></ambiguity_options>'
        )
        cleaned, opts = strip_ambiguity_markup(raw)
        self.assertEqual(len(opts), 1)
        self.assertNotIn("ambiguity_options", cleaned)
        self.assertNotIn("<option", cleaned)

    def test_incomplete_open_block(self) -> None:
        text = (
            "<ambiguity_options>\n"
            '<option discipline="python" slug="a" label="A"/>\n'
            '<option discipline="sql" slug="b" label="B"/>\n'
            "</ambiguity_opt"
        )
        opts = parse_incomplete_ambiguity_options(text)
        self.assertEqual(len(opts), 2)

    def test_incomplete_pair_close_option(self) -> None:
        text = (
            "<ambiguity_options>\n"
            '<option discipline="python" slug="a" label="A"></option>\n'
            '<option discipline="sql" slug="b" label="B"></option>\n'
        )
        opts = parse_incomplete_ambiguity_options(text)
        self.assertEqual(len(opts), 2)
        self.assertEqual(opts[1]["slug"], "b")

    def test_incomplete_rejects_cut_attribute(self) -> None:
        text = (
            "<ambiguity_options>\n"
            '<option discipline="python" slug="ok" label="Completa"/>\n'
            '<option slug="x" title="Introdução à Inteligência\n'
        )
        opts = parse_incomplete_ambiguity_options(text)
        self.assertEqual(len(opts), 1)
        self.assertEqual(opts[0]["slug"], "ok")

    def test_attrs_well_formed(self) -> None:
        from engine.disambiguation_parse import _option_attrs_well_formed

        self.assertFalse(_option_attrs_well_formed('title="sem fecho'))
        self.assertTrue(_option_attrs_well_formed('slug="a" label="b"'))


if __name__ == "__main__":
    unittest.main()
