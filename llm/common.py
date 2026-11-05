# -*- coding: utf-8 -*-
"""Shared helpers for the THEE LLM work: run THEE code safely, call a model, pull code out of replies.

Model backends (pick with --model):
  ollama:<name>        local Ollama, e.g. ollama:qwen2.5-coder:7b or ollama:thee
  openai:<name>@<url>  any OpenAI-compatible server, e.g. openai:thee@http://localhost:8080/v1 (mlx_lm.server)
  anthropic:<name>     Anthropic API (needs ANTHROPIC_API_KEY), e.g. anthropic:claude-sonnet-5-5
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "bin", "thee_cli.py")


# ── Running THEE ─────────────────────────────────────────────────────────

def run_thee(code, timeout=5, max_mem=512):
    """Run THEE code in sandbox mode in a separate process.
    Returns dict(ok, stdout, stderr, timeout)."""
    with tempfile.NamedTemporaryFile("w", suffix=".th", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    env = dict(os.environ, THEE_SANDBOX="1", PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run([sys.executable, CLI, "--sandbox", "--timeout", str(timeout),
                            "--max-mem", str(max_mem), path],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout + 5, env=env, cwd=tempfile.gettempdir())
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr.strip(),
                "timeout": r.returncode == 124}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout", "timeout": True}
    finally:
        os.unlink(path)


def run_with_tests(solution, tests):
    """Run a solution followed by THEE test lines (assert_eq ...). Passing = exit 0."""
    code = solution.rstrip() + "\n\n// ── tests ──\n" + "\n".join(tests) + '\nmoochhu "ALL_TESTS_PASSED"\n'
    res = run_thee(code)
    res["passed"] = res["ok"] and "ALL_TESTS_PASSED" in res["stdout"]
    return res


# ── Pulling code from model replies ──────────────────────────────────────

_FENCE = re.compile(r"```(?:thee|tamil|THEE)?[ \t]*\n(.*?)```", re.S)


def extract_code(reply):
    """First fenced block (```thee ...```), else the whole reply."""
    m = _FENCE.search(reply or "")
    return (m.group(1) if m else (reply or "")).strip()


# ── Calling a model ──────────────────────────────────────────────────────

def _post(url, payload, headers, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def chat(model, messages, system=None, temperature=0.2, max_tokens=2048):
    """Send a chat to the chosen backend and return the reply text."""
    kind, _, name = model.partition(":")
    if kind == "ollama":
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        out = _post(f"{host}/api/chat", {"model": name, "messages": msgs, "stream": False,
                                         "options": {"temperature": temperature,
                                                     "num_predict": max_tokens}}, {})
        return out["message"]["content"]
    if kind == "openai":
        name, _, base = name.partition("@")
        base = base or os.environ.get("OPENAI_BASE_URL", "http://localhost:8080/v1")
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        key = os.environ.get("OPENAI_API_KEY", "none")
        out = _post(f"{base.rstrip('/')}/chat/completions",
                    {"model": name, "messages": msgs, "temperature": temperature,
                     "max_tokens": max_tokens}, {"Authorization": f"Bearer {key}"})
        return out["choices"][0]["message"]["content"]
    if kind == "anthropic":
        key = os.environ["ANTHROPIC_API_KEY"]
        payload = {"model": name, "max_tokens": max_tokens, "temperature": temperature,
                   "messages": messages}
        if system:
            payload["system"] = system
        out = _post("https://api.anthropic.com/v1/messages", payload,
                    {"x-api-key": key, "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in out["content"])
    raise ValueError(f"Unknown model backend '{kind}'. Use ollama:, openai: or anthropic:")


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows, mode="w"):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
