# -*- coding: utf-8 -*-
"""
THEE v6.0 — Tamil-English Programming Language
Command-line interface

Usage:
    thee                     → Start REPL
    thee file.th             → Run a THEE file (.th, or the older .thee)
    thee -e "code"           → Execute inline code
    thee -v                  → Show version
    thee -h                  → Show help
    thee --sandbox file.thee → Run untrusted code (no files/network/shell, 10s, 512MB)
"""

import sys
import os

# Add source to path
THEE_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(THEE_HOME, 'src'))

from thee_lang.lexer import TheeLexer
from thee_lang.parser import TheeParser
from thee_lang.interpreter import TheeInterpreter
from thee_lang import sandbox as thee_sandbox

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
        msg = str(e) or type(e).__name__
        if isinstance(e, MemoryError):
            msg = "memory limit reached (நினைவக வரம்பு முடிந்தது)"
        print(f"தீ பிழை: {msg}", file=sys.stderr)
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
    print("  thee <file.th>           Run a THEE file (.th or .thee)")
    print("  thee -e \"code\"           Execute inline code")
    print("  thee -v, --version       Show version")
    print("  thee -h, --help          Show this help")
    print("  --sandbox                Block files, network, shell, GPIO, Python imports")
    print("  --timeout N              Stop after N seconds (sandbox default: 10)")
    print("  --max-mem MB             Memory cap in MB (sandbox default: 512)")
    print()
    print("Examples:")
    print("  thee hello.th")
    print("  thee -e \"moochhu 21 * 2\"")
    print("  thee -e \"na x = [1,2,3]; ozhugu for i ul x { moochhu i }\"")

def parse_safety_flags(args):
    """Pull --sandbox / --timeout / --max-mem out of args."""
    sandbox = thee_sandbox.sandbox_requested(); timeout = None; max_mem = None; rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--sandbox': sandbox = True
        elif a in ('--timeout', '--max-mem') and i + 1 < len(args):
            try: val = int(args[i + 1])
            except ValueError:
                print(f"Error: {a} needs a number", file=sys.stderr); sys.exit(1)
            if a == '--timeout': timeout = val
            else: max_mem = val
            i += 1
        else: rest.append(a)
        i += 1
    if sandbox:
        os.environ['THEE_SANDBOX'] = '1'  # every interpreter (and imported module) inherits it
        timeout = timeout or 10; max_mem = max_mem or 512
    thee_sandbox.apply_resource_limits(timeout, max_mem)
    return rest

def main():
    args = parse_safety_flags(sys.argv[1:])

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
    elif args[0].endswith(('.th', '.thee')) or os.path.isfile(args[0]):
        run_file(args[0])
    else:
        # Try as inline code
        code = ' '.join(args)
        if not run_code(code):
            sys.exit(1)

if __name__ == '__main__':
    main()
