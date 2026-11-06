# -*- coding: utf-8 -*-
"""THEE tutor with verification: it never shows code it has not run.

For every answer:
  1. the model writes THEE code plus a few assert_eq checks of its own,
  2. the code runs in sandbox mode (no files, network or shell; 5 s limit),
  3. on any error or failed check, the real error goes back to the model (up to 2 retries),
  4. the reply shows the code, its *real* output from the interpreter, and a verdict:
       ✅ ஓடி சரிபார்த்தது  (ran, all checks passed)
       ⚠️ சரிபார்க்க முடியல  (still failing after retries: shown with the error, never as working)
Names the model uses that THEE doesn't have are caught by the interpreter ("Undefined: ...").

  python3 llm/tutor.py "ஒரு list-ல பெரிய number கண்டுபிடிக்கிற function எழுதுங்க"
  python3 llm/tutor.py --model ollama:thee          # interactive
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import chat, extract_code, run_thee  # noqa: E402
from prompts import SYSTEM_TUTOR  # noqa: E402

CHECK_RULE = ("\nCode-க்கு கீழ 2-3 `assert_eq(...)` checks எழுதுங்க (அதே ```thee block-ல), "
              "அப்போ தான் code சரியான்னு run பண்ணி பார்க்க முடியும்.")
_ASSERT = re.compile(r"^\s*assert_eq\(", re.M)


def _explanation(reply):
    """Text after the code block (the model's explanation)."""
    parts = re.split(r"```(?:thee|THEE)?[ \t]*\n.*?```", reply or "", maxsplit=1, flags=re.S)
    return parts[1].strip() if len(parts) > 1 else ""


def ask(model, question, retries=2, history=None, log=None):
    """Returns dict(verified, code, output, error, explanation, attempts)."""
    msgs = list(history or []) + [{"role": "user", "content": question + CHECK_RULE}]
    last = None
    for attempt in range(1, retries + 2):
        reply = chat(model, msgs, system=SYSTEM_TUTOR, temperature=0.2 if attempt > 1 else 0)
        code = extract_code(reply)
        res = run_thee(code)
        has_checks = bool(_ASSERT.search(code))
        ok = res["ok"] and has_checks
        last = {"verified": ok, "code": code, "output": res["stdout"].strip(),
                "error": res["stderr"].strip(), "explanation": _explanation(reply), "attempts": attempt}
        if log:
            log(f"  attempt {attempt}: {'ok' if ok else (res['stderr'].splitlines() or ['no checks'])[-1][:120]}")
        if ok:
            return last
        problem = res["stderr"].strip() or "Code-ல assert_eq checks இல்ல."
        msgs += [{"role": "assistant", "content": reply},
                 {"role": "user", "content":
                  f"இந்த code THEE-ல run பண்ணும்போது இந்த பிரச்சனை வந்துச்சு:\n```\n{problem[-800:]}\n```\n"
                  "என்ன தப்புன்னு ஒரு வரியில சொல்லி, சரியான முழு code-ஐ checks-ஓட குடுங்க."}]
    return last


def render(r):
    lines = ["```thee", r["code"], "```"]
    if r["verified"]:
        lines.append(f"✅ ஓடி சரிபார்த்தது (ran in THEE, all checks passed, attempt {r['attempts']})")
        if r["output"]:
            lines += ["Output:", "```", r["output"], "```"]
        if r["explanation"]:
            lines += ["", r["explanation"]]
    else:
        lines.append("⚠️ சரிபார்க்க முடியல: this code still fails in THEE, so don't trust it yet.")
        lines += ["Error:", "```", (r["error"] or "no assert_eq checks")[-600:], "```",
                  "கேள்வியை கொஞ்சம் மாத்தி கேளுங்க, இல்லன்னா சின்ன parts-ஆ பிரிச்சு கேளுங்க."]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="*")
    ap.add_argument("--model", default=os.environ.get("THEE_MODEL", "ollama:thee"))
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    log = (lambda s: print(s, file=sys.stderr)) if a.verbose else None
    if a.question:
        print(render(ask(a.model, " ".join(a.question), a.retries, log=log)))
        return
    print("THEE tutor — தமிழ்ல கேளுங்க (Ctrl+D to quit)")
    while True:
        try:
            q = input("\n> ").strip()
        except EOFError:
            break
        if q:
            print(render(ask(a.model, q, a.retries, log=log)))


if __name__ == "__main__":
    main()
