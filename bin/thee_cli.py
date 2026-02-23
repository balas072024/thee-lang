# -*- coding: utf-8 -*-
"""
THEE v6.0 — Tamil-English Programming Language
Command-line interface

Usage:
    thee                     → Start REPL
    thee file.thee           → Run a .thee file
    thee -e "code"           → Execute inline code
    thee -v                  → Show version
    thee -h                  → Show help
"""

import sys
import os

# Add source to path
THEE_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(THEE_HOME, 'src'))

from thee_lang.lexer import TheeLexer
from thee_lang.parser import TheeParser
from thee_lang.interpreter import TheeInterpreter

VERSION = "6.0.0"
BANNER = f"""
  ╔═══════════════════════════════════════╗
  ║   THEE v{VERSION} — தீ மொழி              ║
  ║   Tamil-English Programming Language  ║
  ║   443+ builtins · Classes · Agents    ║
  ╚═══════════════════════════════════════╝
"""

def run_code(code, interp=None):
    """Execute THEE source code"""
    if interp is None:
        interp = TheeInterpreter()
    try:
        lexer = TheeLexer(code)
        tokens = lexer.tokenize()
        parser = TheeParser(tokens)
        ast = parser.parse()
        for stmt in ast.statements:
            interp.execute(stmt)
    except Exception as e:
        print(f"தீ பிழை: {e}", file=sys.stderr)
        return False
    return True

def run_file(filepath):
    """Execute a .thee file"""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()
    if not run_code(code):
        sys.exit(1)

def run_repl():
    """Interactive REPL"""
    print(BANNER)
    print("  Type 'exit' or 'வெளி' to quit")
    print("  Type 'help' for commands")
    print()

    interp = TheeInterpreter()
    buffer = []
    brace_count = 0

    while True:
        try:
            prompt = "thee> " if not buffer else "  ... "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nவணக்கம்! (Goodbye!)")
            break

        stripped = line.strip()
        if stripped in ('exit', 'quit', 'வெளி'):
            print("வணக்கம்! (Goodbye!)")
            break
        if stripped == 'help':
            print("  Commands:")
            print("    exit/quit/வெளி  — Exit REPL")
            print("    help            — Show this help")
            print("    clear           — Clear screen")
            print("    version         — Show version")
            print()
            print("  THEE basics:")
            print("    na x = 42                    — Variable")
            print("    moochhu \"Hello\"               — Print")
            print("    thee add(a, b) { kanal a+b } — Function")
            print("    vagu Dog { thee init(n) { self.name = n } }")
            print()
            continue
        if stripped == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
            continue
        if stripped == 'version':
            print(f"  THEE v{VERSION}")
            continue
        if not stripped:
            continue

        # Track braces for multi-line input
        brace_count += line.count('{') - line.count('}')
        buffer.append(line)

        if brace_count <= 0:
            code = '\n'.join(buffer)
            buffer = []
            brace_count = 0
            run_code(code, interp)

def show_help():
    print(f"THEE v{VERSION} — Tamil-English Programming Language")
    print()
    print("Usage:")
    print("  thee                     Start interactive REPL")
    print("  thee <file.thee>         Run a .thee file")
    print("  thee -e \"code\"           Execute inline code")
    print("  thee -v, --version       Show version")
    print("  thee -h, --help          Show this help")
    print()
    print("Examples:")
    print("  thee hello.thee")
    print("  thee -e \"moochhu 21 * 2\"")
    print("  thee -e \"na x = [1,2,3]; ozhugu for i ul x { moochhu i }\"")

def main():
    args = sys.argv[1:]

    if not args:
        run_repl()
        return

    if args[0] in ('-h', '--help'):
        show_help()
    elif args[0] in ('-v', '--version'):
        print(f"THEE v{VERSION}")
    elif args[0] in ('-e', '--eval'):
        if len(args) < 2:
            print("Error: -e requires code argument", file=sys.stderr)
            sys.exit(1)
        code = ' '.join(args[1:])
        if not run_code(code):
            sys.exit(1)
    elif args[0].endswith('.thee') or os.path.isfile(args[0]):
        run_file(args[0])
    else:
        # Try as inline code
        code = ' '.join(args)
        if not run_code(code):
            sys.exit(1)

if __name__ == '__main__':
    main()
