# -*- coding: utf-8 -*-
"""Phase 2 — build verified Python→THEE training data (MultiPL-T style).

For every Python task:
  1. convert its Python asserts to THEE assert_eq tests (deterministic when possible,
     otherwise the model translates them),
  2. ask a strong model to translate the Python solution to THEE,
  3. run the THEE solution + tests in sandbox mode; on failure, show the model the
     error and let it retry (these retries become "fix the error" training data),
  4. keep only passing pairs, then ask for a spoken-Tamil task description and a
     short Tamil explanation.

Sources:
  --source mbpp            MBPP (needs `pip install datasets`; run on your Mac)
  --source humaneval       OpenAI HumanEval (same)
  --source file.jsonl      your own rows: {"id", "text", "code", "tests": ["assert f(1) == 2", ...]}

Example (Mac, with Ollama running a strong local coder, or the Anthropic API):
  python3 llm/pipeline/translate.py --source mbpp --model anthropic:claude-sonnet-5-5 --out llm/data/verified.jsonl
  python3 llm/pipeline/translate.py --source mbpp --model ollama:qwen2.5-coder:32b --limit 50

Safe to stop and restart: rows already in --out are skipped.
"""
import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import chat, read_jsonl, run_with_tests, write_jsonl  # noqa: E402
from prompts import reference_text  # noqa: E402

_lock = threading.Lock()

# ── sources ──────────────────────────────────────────────────────────────

def load_source(source, limit=0):
    if source in ("mbpp", "humaneval"):
        try:
            from datasets import load_dataset
        except ImportError:
            sys.exit("Install the datasets package first:  pip install datasets")
        rows = []
        if source == "mbpp":
            ds = load_dataset("google-research-datasets/mbpp", "sanitized")
            for split in ("train", "validation", "test", "prompt"):
                for r in ds[split]:
                    rows.append({"id": f"mbpp-{r['task_id']}", "text": r["prompt"],
                                 "code": r["code"], "tests": list(r["test_list"])})
        else:
            ds = load_dataset("openai/openai_humaneval")["test"]
            for r in ds:
                tests = [ln.strip() for ln in r["test"].splitlines() if ln.strip().startswith("assert")]
                tests = [t.replace("candidate(", r["entry_point"] + "(") for t in tests]
                rows.append({"id": r["task_id"].replace("/", "-"), "text": r["prompt"],
                             "code": r["prompt"] + r["canonical_solution"], "tests": tests})
    else:
        rows = read_jsonl(source)
    return rows[:limit] if limit else rows


# ── Python assert → THEE assert_eq ───────────────────────────────────────

_PY_LIT = {"True": "unmai", "False": "poi", "None": "sambal"}


def _split_top_level(expr, sep="=="):
    depth, quote, i = 0, None, 0
    while i < len(expr):
        ch = expr[i]
        if quote:
            if ch == "\\":
                i += 2; continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and expr.startswith(sep, i) and expr[i - 1:i] not in "!<>=" and expr[i + 2:i + 3] != "=":
            return expr[:i].strip(), expr[i + 2:].strip()
        i += 1
    return None


def _swap_literals(expr):
    out, i, quote = [], 0, None
    while i < len(expr):
        ch = expr[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < len(expr):
                out.append(expr[i + 1]); i += 2; continue
            if ch == quote:
                quote = None
            i += 1; continue
        if ch in "\"'":
            quote = ch; out.append(ch); i += 1; continue
        m = re.match(r"[A-Za-z_]\w*", expr[i:])
        if m:
            w = m.group(0); out.append(_PY_LIT.get(w, w)); i += len(w); continue
        out.append(ch); i += 1
    return "".join(out)


def python_assert_to_thee(line):
    """'assert f(1, [2]) == True' → 'assert_eq(f(1, [2]), unmai)'. None if it can't be done safely."""
    s = line.strip()
    if not s.startswith("assert "):
        return None
    body = s[len("assert "):].strip()
    parts = _split_top_level(body, "==")
    if parts is None:
        return None
    # Python-only syntax we won't convert mechanically (sets, tuples, math, comprehensions)
    if re.search(r"\bset\(|\btuple\(|\bmath\.|\blambda\b|\bfor\b|\bisclose\b|[{]\s*[^:}]+[,}]", body):
        return None
    lhs, rhs = parts
    if re.search(r"(?<![\w\]\)])\(\s*[^()]*,", lhs) or rhs.startswith("(") or ("'" in body and '"' in body):
        return None  # tuple result, or mixed quotes we can't safely normalise
    lhs = _swap_literals(lhs.replace("'", '"'))
    rhs = _swap_literals(rhs.replace("'", '"'))
    return f"assert_eq({lhs}, {rhs})"


# ── model calls ──────────────────────────────────────────────────────────

TRANSLATE_SYSTEM = """You translate Python programs into THEE. Follow the THEE reference exactly.
Keep the same function name and argument order. Use romanized keywords (na, thee, kanal, endral, allathu, illai, ozhugu, ul, varai).
Reply with exactly one ```thee code block containing only the function(s) — no tests, no prints.

""" + reference_text()

TESTS_SYSTEM = """Translate these Python assert statements into THEE test lines of the form
assert_eq(<call>, <expected>). Python True/False/None become unmai/poi/sambal. Tuples become lists.
Reply with one ```thee block containing only the assert_eq lines, one per input assert, same order.

""" + reference_text()

TAMIL_SYSTEM = """You write for Tamil learners in everyday spoken Tamil (பேச்சு தமிழ், the way people talk today,
technical words like function, list, number stay in English). Reply in exactly this format:
<task_ta>one or two sentences: the task, as a student would ask for it (a request, not a question
about the code; never mention Python)</task_ta>
<explain_ta>2-4 short sentences explaining how the THEE code works</explain_ta>"""


def _blocks(reply):
    return [b.strip() for b in re.findall(r"```(?:thee|THEE)?[ \t]*\n(.*?)```", reply or "", re.S)]


def translate_tests(model, py_tests):
    thee = [python_assert_to_thee(t) for t in py_tests]
    if all(thee):
        return thee, "rule"
    reply = chat(model, [{"role": "user", "content": "\n".join(py_tests)}], system=TESTS_SYSTEM, temperature=0)
    b = _blocks(reply)
    lines = [ln.strip() for ln in (b[0] if b else "").splitlines() if ln.strip().startswith("assert_eq(")]
    return (lines, "model") if len(lines) == len(py_tests) else (None, "model")


def translate_one(model, row, retries):
    tests, how = translate_tests(model, row["tests"])
    if not tests:
        return None, []
    msgs = [{"role": "user", "content":
             f"Task: {row['text']}\n\nPython solution:\n```python\n{row['code']}\n```\n\n"
             f"It must pass these THEE tests:\n```thee\n" + "\n".join(tests) + "\n```"}]
    repairs = []
    for attempt in range(retries + 1):
        reply = chat(model, msgs, system=TRANSLATE_SYSTEM, temperature=0.2 if attempt else 0)
        b = _blocks(reply)
        code = b[0] if b else ""
        res = run_with_tests(code, tests)
        if res["passed"]:
            return {"code": code, "tests": tests, "tests_from": how, "attempts": attempt + 1}, repairs
        err = (res["stderr"] or "no output")[-600:]
        if code:
            repairs.append({"bad_code": code, "error": err})
        msgs += [{"role": "assistant", "content": reply},
                 {"role": "user", "content": f"That fails in THEE with:\n{err}\nFix it. Reply with the full corrected ```thee block."}]
    return None, repairs


def tamil_text(model, row, code):
    reply = chat(model, [{"role": "user", "content":
                          f"Task (English): {row['text']}\n\nTHEE solution:\n```thee\n{code}\n```"}],
                 system=TAMIL_SYSTEM, temperature=0.4)
    t = re.search(r"<task_ta>(.*?)</task_ta>", reply, re.S)
    e = re.search(r"<explain_ta>(.*?)</explain_ta>", reply, re.S)
    return (t.group(1).strip() if t else ""), (e.group(1).strip() if e else "")


def _fn_name(code):
    m = re.search(r"\b(?:thee|தீ)\s+([^\s(]+)\s*\(", code)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "data", "verified.jsonl"))
    ap.add_argument("--repairs-out", default=os.path.join(os.path.dirname(HERE), "data", "repairs.jsonl"))
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-tamil", action="store_true", help="skip the Tamil description step")
    ap.add_argument("--tamil-model", default="", help="separate model for the Tamil text (default: --model)")
    ap.add_argument("--retry-failed", action="store_true", help="try tasks that failed in an earlier run again")
    a = ap.parse_args()

    rows = load_source(a.source, a.limit)
    failed_log = os.path.splitext(a.out)[0] + ".failed.jsonl"
    done = {r["id"] for r in read_jsonl(a.out)} if os.path.exists(a.out) else set()
    if not a.retry_failed and os.path.exists(failed_log):
        done |= {r["id"] for r in read_jsonl(failed_log)}
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} tasks, {len(done)} already done, {len(todo)} to go")
    stats = {"ok": 0, "fail": 0}

    def work(row):
        try:
            got, repairs = translate_one(a.model, row, a.retries)
        except Exception as e:
            print(f"  ! {row['id']}: {e}", flush=True)
            return
        if not got:
            with _lock:
                stats["fail"] += 1
                write_jsonl(failed_log, [{"id": row["id"]}], mode="a")
            print(f"  ✗ {row['id']}", flush=True)
            return
        task_ta, explain_ta = "", ""
        if not a.no_tamil:
            try:
                task_ta, explain_ta = tamil_text(a.tamil_model or a.model, row, got["code"])
            except Exception as e:  # a slow/failed Tamil reply must not lose the verified code
                print(f"  ! {row['id']}: Tamil text skipped ({e})", flush=True)
        out = {"id": row["id"], "source": a.source if a.source in ("mbpp", "humaneval") else "file",
               "fn": _fn_name(got["code"]), "prompt_en": row["text"].strip(), "prompt_ta": task_ta,
               "python": row["code"], "thee": got["code"], "tests": got["tests"],
               "tests_from": got["tests_from"], "attempts": got["attempts"], "explain_ta": explain_ta}
        with _lock:
            write_jsonl(a.out, [out], mode="a")
            # A repair example is only useful when the final fixed code is known.
            if repairs:
                write_jsonl(a.repairs_out, [{"id": row["id"], "prompt_en": out["prompt_en"],
                                             "bad_code": rp["bad_code"], "error": rp["error"],
                                             "fixed_code": got["code"]} for rp in repairs], mode="a")
            stats["ok"] += 1
        print(f"  ✓ {row['id']} ({got['attempts']} attempt{'s' if got['attempts'] > 1 else ''}, tests by {got['tests_from']})", flush=True)

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(work, todo))
    total = stats["ok"] + stats["fail"]
    print(f"\nverified {stats['ok']}/{total}" + (f" ({stats['ok'] / total:.0%})" if total else "") + f" → {a.out}")


if __name__ == "__main__":
    main()
