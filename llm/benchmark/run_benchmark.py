# -*- coding: utf-8 -*-
"""Score a model on the THEE-Tamil benchmark: ask it each task, run its code with the tests in sandbox mode.

  python3 llm/benchmark/run_benchmark.py --model ollama:thee
  python3 llm/benchmark/run_benchmark.py --model ollama:qwen2.5-coder:7b --with-reference   # base model + language guide
  python3 llm/benchmark/run_benchmark.py --model anthropic:claude-sonnet-5-5 --with-reference --lang en
  python3 llm/benchmark/run_benchmark.py --check-references                                 # no model, sanity check

Reports pass@1 (and pass@k with --samples k). Results go to llm/benchmark/results/<model>.jsonl.
"""
import argparse
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import chat, extract_code, read_jsonl, run_with_tests, write_jsonl  # noqa: E402
from prompts import SYSTEM_CODER, SYSTEM_TUTOR, reference_text, task_prompt  # noqa: E402


def attempt_verified(model, task, lang):
    """Tutor loop: the model only sees its own checks and real errors, never the hidden tests."""
    from tutor import ask
    t0 = time.time()
    try:
        r = ask(model, task_prompt(task, lang))
    except Exception as e:
        return {"passed": False, "error": f"model error: {e}", "code": "", "seconds": time.time() - t0}
    res = run_with_tests(r["code"], task["tests"])
    return {"passed": res["passed"], "error": res["stderr"][-400:], "code": r["code"],
            "self_verified": r["verified"], "ran": r.get("ran", False), "loop_attempts": r["attempts"],
            "seconds": round(time.time() - t0, 2)}


def attempt(model, task, lang, system, temperature):
    t0 = time.time()
    try:
        reply = chat(model, [{"role": "user", "content": task_prompt(task, lang)}],
                     system=system, temperature=temperature)
    except Exception as e:  # network / model errors count as failures
        return {"passed": False, "error": f"model error: {e}", "code": "", "seconds": time.time() - t0}
    code = extract_code(reply)
    res = run_with_tests(code, task["tests"])
    return {"passed": res["passed"], "error": res["stderr"][-400:], "code": code,
            "seconds": round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="ollama:<name> | openai:<name>@<url> | anthropic:<name>")
    ap.add_argument("--tasks", default=os.path.join(HERE, "tasks.jsonl"))
    ap.add_argument("--lang", choices=["ta", "en"], default="ta", help="prompt language (default Tamil)")
    ap.add_argument("--with-reference", action="store_true", help="put the THEE language guide in the system prompt")
    ap.add_argument("--system", choices=["coder", "tutor", "none"], default="coder",
                    help="system prompt: coder (base models), tutor (THEE fine-tunes, as trained), none (Ollama model's own)")
    ap.add_argument("--samples", type=int, default=1, help="attempts per task (pass@k)")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--check-references", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="use the tutor's run-check-fix loop (tutor prompt, up to 2 retries on its own checks)")
    a = ap.parse_args()

    tasks = read_jsonl(a.tasks)
    if a.limit:
        tasks = tasks[:a.limit]

    if a.check_references:
        bad = [t["id"] for t in tasks if not run_with_tests(t["reference"], t["tests"])["passed"]]
        print(f"references: {len(tasks) - len(bad)}/{len(tasks)} pass", *bad)
        return 1 if bad else 0
    if not a.model:
        ap.error("--model is required (or use --check-references)")

    system = {"coder": SYSTEM_CODER, "tutor": SYSTEM_TUTOR, "none": ""}[a.system]
    if a.with_reference:
        system = (system + "\n\n" + reference_text()).strip()
    system = system or None
    temp = a.temperature if a.samples == 1 else max(a.temperature, 0.6)

    def run_task(t):
        if a.verify:
            tries = [attempt_verified(a.model, t, a.lang) for _ in range(a.samples)]
        else:
            tries = [attempt(a.model, t, a.lang, system, temp) for _ in range(a.samples)]
        return {"id": t["id"], "fn": t["fn"], "pass1": tries[0]["passed"],
                "passk": any(x["passed"] for x in tries), "attempts": tries}

    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(run_task, tasks), 1):
            rows.append(r)
            mark = "✓" if r["pass1"] else "✗"
            print(f"[{i:3d}/{len(tasks)}] {mark} {r['id']} {r['fn']}", flush=True)

    n = len(rows)
    p1 = sum(r["pass1"] for r in rows) / n
    pk = sum(r["passk"] for r in rows) / n
    tag = (re.sub(r"[^A-Za-z0-9._-]+", "_", a.model) + f"_{a.lang}" + ("_ref" if a.with_reference else "")
           + ("" if a.system == "coder" else f"_{a.system}") + ("_verify" if a.verify else ""))
    out = os.path.join(HERE, "results", f"{tag}.jsonl")
    write_jsonl(out, rows)
    print(f"\n{a.model} ({a.lang}{', with guide' if a.with_reference else ''}): "
          f"pass@1 = {p1:.1%}" + (f", pass@{a.samples} = {pk:.1%}" if a.samples > 1 else ""))
    if a.verify:
        shown = [r for r in rows if r["attempts"][0].get("self_verified")]
        wrong = sum(not r["pass1"] for r in shown)
        print(f"shown as ✅ verified: {len(shown)}/{n}; of those, wrong on hidden tests: {wrong}"
              f" ({wrong / max(1, len(shown)):.0%})")
        ran = [r for r in rows if not r["attempts"][0].get("self_verified") and r["attempts"][0].get("ran")]
        print(f"shown as 🟡 runs-but-unchecked: {len(ran)}; shown as ⚠️ failing: {n - len(shown) - len(ran)}")
    print(f"details: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
