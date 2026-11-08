# -*- coding: utf-8 -*-
"""Checks for the LLM tooling: keyword conversion, assert conversion, benchmark, lessons, reference guide."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "llm"))
sys.path.insert(0, os.path.join(ROOT, "llm", "pipeline"))

from common import read_jsonl, run_thee, run_with_tests  # noqa: E402
from tamil_script import convert  # noqa: E402
from translate import python_assert_to_thee  # noqa: E402


class TamilScriptTests(unittest.TestCase):
    def test_round_trip_keeps_behaviour(self):
        for name in ["hello.th", "calculator.th", "tamil.th"]:
            src = open(os.path.join(ROOT, "examples", name), encoding="utf-8").read()
            base = run_thee(src)["stdout"]
            tamil = convert(src, "tamil")
            with self.subTest(example=name):
                self.assertEqual(run_thee(tamil)["stdout"], base)
                self.assertEqual(run_thee(convert(tamil, "roman"))["stdout"], base)

    def test_strings_comments_members_untouched(self):
        self.assertEqual(convert('moochhu "moochhu" // moochhu\nx.match', "tamil"),
                         'மூச்சு "moochhu" // moochhu\nx.match')


class AssertConversionTests(unittest.TestCase):
    def test_converts_simple_asserts(self):
        self.assertEqual(python_assert_to_thee("assert f('a', [1]) == True"), 'assert_eq(f("a", [1]), unmai)')
        self.assertEqual(python_assert_to_thee("assert g() == None"), "assert_eq(g(), sambal)")

    def test_refuses_python_only_syntax(self):
        for t in ["assert f((1, 2)) == 3", "assert f(1) == (1, 2)", "assert set(f()) == set([1])",
                  "assert math.isclose(f(1), 2.0)", "assert f(1) != 2"]:
            with self.subTest(t=t):
                self.assertIsNone(python_assert_to_thee(t))


class DataChecks(unittest.TestCase):
    def test_benchmark_references_pass(self):
        tasks = read_jsonl(os.path.join(ROOT, "llm", "benchmark", "tasks.jsonl"))
        self.assertGreaterEqual(len(tasks), 100)
        bad = [t["id"] for t in tasks if not run_with_tests(t["reference"], t["tests"])["passed"]]
        self.assertEqual(bad, [])

    def test_reference_guide_examples_run(self):
        md = open(os.path.join(ROOT, "llm", "THEE_REFERENCE.md"), encoding="utf-8").read()
        for i, block in enumerate(re.findall(r"```thee\n(.*?)```", md, re.S)):
            with self.subTest(block=i):
                self.assertTrue(run_thee(block)["ok"])


if __name__ == "__main__":
    unittest.main()
