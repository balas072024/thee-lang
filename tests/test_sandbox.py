# -*- coding: utf-8 -*-
"""Tests for the Python bridge (konar python.X) and sandbox mode.
Run: python3 -m unittest discover -s tests -v
"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "bin", "thee_cli.py")
sys.path.insert(0, os.path.join(ROOT, "src"))

from thee_lang.lexer import TheeLexer
from thee_lang.parser import TheeParser
from thee_lang.interpreter import TheeInterpreter
from thee_lang.sandbox import TheeSandboxError


def run(code, sandbox=False):
    interp = TheeInterpreter(sandbox=sandbox)
    interp.run(TheeParser(TheeLexer(code).tokenize()).parse())
    return interp.output


def cli(*args, timeout=30):
    env = dict(os.environ); env.pop("THEE_SANDBOX", None)
    return subprocess.run([sys.executable, CLI, *args], capture_output=True,
                          text=True, encoding="utf-8", timeout=timeout, env=env)


class PythonBridgeTests(unittest.TestCase):
    def test_import_module(self):
        self.assertEqual(run('konar python.math\nmoochhu math.sqrt(16)'), ["4"])
        out = run('konar python.statistics as st\nmoochhu st.mean([1, 2, 3, 4])')
        self.assertEqual(out, ["2.5"])

    def test_dotted_import_and_alias(self):
        self.assertEqual(run('konar python.os.path as p\nmoochhu p.join("a", "b")'), ["a/b" if os.sep == "/" else "a\\b"])

    def test_default_alias_is_last_segment(self):
        self.assertEqual(run('konar python.os.path\nmoochhu path.basename("x/y.txt")'), ["y.txt"])

    def test_missing_module(self):
        with self.assertRaises(Exception):
            run('konar python.no_such_module_xyz')


class SandboxBlocksTests(unittest.TestCase):
    BLOCKED = [
        'read_file("/etc/passwd")',
        'write_file("x.txt", "hi")',
        'file_delete("x.txt")',
        'exec_cmd("id")',
        'pip_install("requests")',
        'py_import("os")',
        'py_eval("1+1")',
        'py_exec("print(1)")',
        'http_get("https://example.com")',
        'fetch("https://example.com")',
        'web_serve(8000)',
        'gpio_high(18)',
        'env_get("HOME")',
        'ai_complete("hi")',
        'docker_gen("app")',
    ]

    def test_blocked_builtins(self):
        for call in self.BLOCKED:
            with self.subTest(call=call):
                with self.assertRaises(TheeSandboxError):
                    run(f"moochhu {call}", sandbox=True)

    def test_blocked_imports(self):
        for code in ['konar python.os', 'konar os', 'konar http', 'konar ai', 'konar "other.thee"']:
            with self.subTest(code=code):
                with self.assertRaises(TheeSandboxError):
                    run(code, sandbox=True)

    def test_private_attributes_blocked(self):
        for code in ['moochhu "x".__class__', 'na f = len\nmoochhu f.__globals__',
                     'moochhu "abc".upper.__self__',
                     'moochhu format_str("{0.__class__}", "x")']:
            with self.subTest(code=code):
                with self.assertRaises(TheeSandboxError):
                    run(code, sandbox=True)

    def test_file_db_blocked_memory_db_allowed(self):
        with self.assertRaises(TheeSandboxError):
            run('db_open("evil.db")', sandbox=True)
        self.assertEqual(run('db_open(":memory:")\nmoochhu "ok"', sandbox=True), ["ok"])
        self.assertFalse(os.path.exists("evil.db"))


class SandboxAllowsTests(unittest.TestCase):
    def test_pure_code_runs(self):
        code = ('na total = 0\nozhugu for i ul range(10) { total = total + i }\n'
                'moochhu total\nmoochhu format_str("{} + {}", 2, 3)\nmoochhu upper("tamil")')
        self.assertEqual(run(code, sandbox=True), ["45", "2 + 3", "TAMIL"])

    def test_safe_modules(self):
        self.assertEqual(run('konar math\nmoochhu sqrt(9)', sandbox=True), run('konar math\nmoochhu sqrt(9)'))

    def test_examples_run_in_sandbox(self):
        for name in ["hello.thee", "calculator.thee", "tamil.thee"]:
            with self.subTest(example=name):
                r = cli("--sandbox", os.path.join(ROOT, "examples", name))
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_normal_mode_unchanged(self):
        # Without sandbox, file access still works as before.
        self.assertEqual(run('moochhu len(read_file("' + CLI.replace("\\", "/") + '")) > 0'),
                         run('moochhu true'))


class SandboxCliTests(unittest.TestCase):
    def test_timeout(self):
        r = cli("--sandbox", "--timeout", "2", "-e", "while true { na x = 1 }")
        self.assertEqual(r.returncode, 124)
        self.assertIn("timeout", r.stderr)

    def test_env_var_enables_sandbox(self):
        env = dict(os.environ, THEE_SANDBOX="1")
        r = subprocess.run([sys.executable, CLI, "-e", 'moochhu exec_cmd("id")'],
                           capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sandbox", r.stderr)


if __name__ == "__main__":
    unittest.main()
