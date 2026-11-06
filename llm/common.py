# -*- coding: utf-8 -*-
"""Shared helpers for the THEE LLM work: run THEE code safely, call a model, pull code out of replies.

Model backends (pick with --model):
  ollama:<name>        local Ollama, e.g. ollama:qwen2.5-coder:7b or ollama:thee
  openai:<name>@<url>  any OpenAI-compatible server, e.g. openai:thee@http://localhost:8080/v1 (mlx_lm.server)
  anthropic:<name>     Anthropic API (needs ANTHROPIC_API_KEY; ANTHROPIC_WORKSPACE_ID for keys not
                       scoped to a workspace), e.g. anthropic:claude-sonnet-5-5
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:  # surface the API's own error message
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}") from None


def chat(model, messages, system=None, temperature=0.2, max_tokens=2048):
    """Send a chat to the chosen backend and return the reply text."""
    kind, _, name = model.partition(":")
    if kind == "ollama":
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        payload = {"model": name, "messages": msgs, "stream": False,
                   "options": {"temperature": temperature, "num_predict": max_tokens}}
        if os.environ.get("OLLAMA_THINK", "").lower() in ("0", "false", "off"):
            payload["think"] = False  # faster answers from thinking models (qwen3 etc.)
        out = _post(f"{host}/api/chat", payload, {})
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
        # Current Claude models reject `temperature`, so it is not sent.
        payload = {"model": name, "max_tokens": max_tokens, "messages": messages}
        if system:
            # The system prompt (with the THEE guide) is identical on every call: cache it.
            payload["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        if os.environ.get("ANTHROPIC_WORKSPACE_ID"):  # keys not scoped to a workspace need this
            headers["anthropic-workspace-id"] = os.environ["ANTHROPIC_WORKSPACE_ID"]
        out = _post("https://api.anthropic.com/v1/messages", payload, headers)
        _add_cost(name, out.get("usage", {}))
        return "".join(b.get("text", "") for b in out["content"])
    raise ValueError(f"Unknown model backend '{kind}'. Use ollama:, openai: or anthropic:")


# ── API cost tracking (USD per million tokens: input, output, cache write, cache read) ──
PRICES = {"claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.20), "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
          "claude-fable-5-1": (10.0, 50.0, 12.5, 1.0), "claude-haiku-5-5": (1.0, 5.0, 1.25, 0.10)}
_cost = {"usd": 0.0, "calls": 0}
_cost_lock = threading.Lock()


def _add_cost(model, usage):
    p = PRICES.get(model, PRICES["claude-opus-5-5"])  # unknown model: assume the dearer rate
    usd = (usage.get("input_tokens", 0) * p[0] + usage.get("output_tokens", 0) * p[1]
           + usage.get("cache_creation_input_tokens", 0) * p[2]
           + usage.get("cache_read_input_tokens", 0) * p[3]) / 1e6
    with _cost_lock:
        _cost["usd"] += usd
        _cost["calls"] += 1


def api_cost():
    """Estimated Anthropic API spend so far in this process (USD) and number of calls."""
    with _cost_lock:
        return _cost["usd"], _cost["calls"]


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows, mode="w"):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
