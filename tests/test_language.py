# -*- coding: utf-8 -*-
"""Regression tests for language fixes."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from thee_lang.lexer import TheeLexer
from thee_lang.parser import TheeParser
from thee_lang.interpreter import TheeInterpreter


def run(code):
    i = TheeInterpreter(sandbox=False)
    i.run(TheeParser(TheeLexer(code).tokenize()).parse())
    return i.output


class LanguageTests(unittest.TestCase):
    def test_elif_block_runs_every_statement(self):
        code = 'na x = 2\nendral x == 1 { moochhu "one" } allathu x == 2 {\n moochhu "a"\n moochhu "b"\n}'
        self.assertEqual(run(code), ["a", "b"])

    def test_nested_if_inside_elif(self):
        code = ('thee g(x) {\n endral x == 1 { kanal 1 } allathu x == 2 {\n'
                '  endral x == 5 { kanal 5 }\n  kanal 22\n }\n kanal 0\n}\nmoochhu g(2)')
        self.assertEqual(run(code), ["22"])

    def test_import_th_and_thee_files(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "mathy.th"), "w", encoding="utf-8") as f:
            f.write("thee add(a, b) { kanal a + b }\n")
        with open(os.path.join(d, "old.thee"), "w", encoding="utf-8") as f:
            f.write("thee sub(a, b) { kanal a - b }\n")
        cwd = os.getcwd(); os.chdir(d)
        try:
            self.assertEqual(run('konar "mathy"\nkonar "old"\nmoochhu add(2, 3)\nmoochhu sub(5, 3)'), ["5", "2"])
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
