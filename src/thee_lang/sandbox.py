# -*- coding: utf-8 -*-
"""
THEE sandbox mode — பாதுகாப்பு முறை

Used for running code you did not write yourself (for example code generated
by the THEE LLM). When sandbox mode is on:

  * builtins that touch files, the network, the shell, hardware (GPIO),
    environment variables, AI APIs or code generators are replaced with a
    stub that raises a clear error;
  * `konar python.<module>`, `konar os/http/ai` and file imports are refused;
  * Python attributes starting with "_" cannot be read (blocks escapes such as
    "".__class__.__mro__);
  * the CLI adds a wall-clock timeout and a memory cap (see bin/thee_cli.py).

Turn it on with `thee --sandbox file.th`, the THEE_SANDBOX=1 environment
variable, or TheeInterpreter(sandbox=True).
"""

import os
import re

# Exact builtin names that are blocked.
BLOCKED_NAMES = {
    # files and filesystem
    "read_file", "write_file", "list_dir", "mkdir", "mkdir_p", "cwd",
    "path_exists", "config_load", "config_save", "csv_read", "csv_write",
    # shell / process / Python escape hatches
    "exec_cmd", "thee_shell", "pip_install", "fast_fn", "optimize",
    # network
    "fetch", "telegram_bot",
    # system info
    "disk_free", "cpu_temp", "mem_free", "platform_name", "argv_list", "uptime",
    # background execution that can outlive the timeout
    "schedule", "set_interval", "set_timeout",
    # GUI windows
    "gui_run", "gui_window",
    # web middleware that only makes sense with a server
    "use_cors", "use_logger", "use_auth",
}

# Name patterns that are blocked (whole families of builtins).
BLOCKED_PATTERNS = [
    r"^file_", r"^py_", r"^http_", r"^web_", r"^ws_", r"^gpio_", r"^env_",
    r"^ai_", r"^agent_", r"_gen$", r"_export$",
]

# Built-in modules that cannot be imported in sandbox mode.
BLOCKED_MODULES = {"os", "http", "ai"}

_PATTERNS = [re.compile(p) for p in BLOCKED_PATTERNS]


class TheeSandboxError(Exception):
    """Raised when sandboxed code tries to use a blocked feature."""


def sandbox_requested():
    """True when the THEE_SANDBOX environment variable asks for sandbox mode."""
    return os.environ.get("THEE_SANDBOX", "").strip().lower() in ("1", "true", "yes", "on")


def is_blocked(name):
    if name in BLOCKED_NAMES:
        return True
    return any(p.search(name) for p in _PATTERNS)


def _blocked_stub(name):
    def stub(*args, **kwargs):
        raise TheeSandboxError(
            f"'{name}' is blocked in sandbox mode "
            f"(பாதுகாப்பு முறையில் '{name}' அனுமதி இல்லை)"
        )
    stub.__name__ = f"blocked_{name}"
    return stub


def _safe_db_open(real_db_open):
    """Allow only in-memory databases."""
    def db_open(path=":memory:", *args, **kwargs):
        if path != ":memory:":
            raise TheeSandboxError(
                "db_open only allows ':memory:' in sandbox mode "
                "(பாதுகாப்பு முறையில் நினைவக தரவுத்தளம் மட்டும்)"
            )
        return real_db_open(path, *args, **kwargs)
    return db_open


def _safe_format_str(template, *args):
    """str.format without attribute/index traversal into private members."""
    import string

    class _SafeFormatter(string.Formatter):
        def get_field(self, field_name, a, kw):
            if any(part.startswith("_") for part in re.split(r"[.\[\]]", field_name)):
                raise TheeSandboxError(
                    f"format field '{field_name}' is blocked in sandbox mode")
            return super().get_field(field_name, a, kw)

    return _SafeFormatter().format(str(template), *args) if args else template


def apply_sandbox(interp):
    """Replace every blocked builtin in the interpreter's global environment.
    Returns the sorted list of names that were blocked."""
    bindings = interp.env.bindings
    blocked = []
    for name in list(bindings):
        if is_blocked(name):
            bindings[name] = _blocked_stub(name)
            blocked.append(name)
    if "format_str" in bindings:
        bindings["format_str"] = _safe_format_str
    if "db_open" in bindings:
        bindings["db_open"] = _safe_db_open(bindings["db_open"])
    return sorted(blocked)


def check_import(path):
    """Raise if sandboxed code may not import this module path."""
    if path.startswith("python.") or path == "python":
        raise TheeSandboxError(
            f"Python imports are blocked in sandbox mode: '{path}' "
            "(பாதுகாப்பு முறையில் Python இறக்குமதி இல்லை)"
        )
    if path in BLOCKED_MODULES:
        raise TheeSandboxError(f"Module '{path}' is blocked in sandbox mode")


def check_file_import(path):
    raise TheeSandboxError(
        f"File imports are blocked in sandbox mode: '{path}' "
        "(பாதுகாப்பு முறையில் கோப்பு இறக்குமதி இல்லை)"
    )


def check_attribute(name):
    """Block private/dunder attribute access on Python objects."""
    if name.startswith("_"):
        raise TheeSandboxError(
            f"Access to '{name}' is blocked in sandbox mode "
            "(பாதுகாப்பு முறையில் தனிப்பட்ட பண்புகள் இல்லை)"
        )


def apply_resource_limits(timeout_s=None, max_mem_mb=None):
    """Wall-clock timeout and memory cap for the current process (Unix only).
    The timeout exits the whole process, so spawned threads cannot outlive it."""
    if timeout_s:
        try:
            import signal

            def _on_timeout(signum, frame):
                import sys
                print(f"தீ பிழை: sandbox timeout after {timeout_s}s "
                      f"(நேர வரம்பு {timeout_s} விநாடி முடிந்தது)", file=sys.stderr)
                sys.stderr.flush(); sys.stdout.flush()
                os._exit(124)

            signal.signal(signal.SIGALRM, _on_timeout)
            signal.alarm(int(timeout_s))
        except (ImportError, AttributeError, ValueError):
            pass  # Windows: no SIGALRM — rely on the Docker sandbox instead
    if max_mem_mb:
        try:
            import resource
            limit = int(max_mem_mb) * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        except (ImportError, ValueError, OSError):
            pass  # not supported on this platform (macOS often ignores RLIMIT_AS)
