# -*- coding: utf-8 -*-
"""Record real THEE tutor answers for the demo video (nothing is staged).

Asks the model each question through the run-check-fix tutor, and saves exactly what came back:
the code, the interpreter's real output, the ✅/🟡/⚠️ verdict, the attempts, and the explanation.
Also records a sandbox block and a Tamil⇄romanized keyword conversion.

  python3 llm/demo/capture.py --model openai:llm/train/fused@http://localhost:8765/v1
"""
import argparse
import json
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pipeline"))
from common import chat, extract_code, read_jsonl, run_thee  # noqa: E402
from prompts import SYSTEM_TUTOR  # noqa: E402
from tamil_script import convert  # noqa: E402
from tutor import ask  # noqa: E402

# (question, sample call we run on the answer, the correct output)
QUESTIONS = [
    ("ரெண்டு number-ஐ கூட்டி return பண்ணுற function எழுதுங்க. Function பேரு `add`.", "moochhu add(7, 5)", "12"),
    ("ஒரு number இரட்டைப்படையா இல்லையான்னு சொல்ற function எழுதுங்க. Function பேரு `is_even`.",
     "moochhu is_even(10)", "உண்மை (true)"),
    ("ஒரு list-ல இருக்கிற numbers-ஓட கூட்டுத்தொகை கண்டுபிடிக்கிற function எழுதுங்க. Function பேரு `list_total`.",
     "moochhu list_total([4, 8, 15])", "27"),
    ("1 முதல் n வரை இரட்டைப்படை numbers-ஐ list-ஆ குடுக்கிற function எழுதுங்க. Function பேரு `evens_upto`.",
     "moochhu evens_upto(10)", "[2, 4, 6, 8, 10]"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "demo.json"))
    ap.add_argument("--score-file", default="", help="benchmark results jsonl for the score scene")
    ap.add_argument("--plain", action="store_true",
                    help="ask once with the tutor prompt (as trained), then run a sample call and compare")
    a = ap.parse_args()

    demos = []
    for q, probe, expected in QUESTIONS:
        if a.plain:
            reply = chat(a.model, [{"role": "user", "content": q}], system=SYSTEM_TUTOR, temperature=0)
            code = extract_code(reply)
            parts = re.split(r"```(?:thee|THEE)?[ \t]*\n.*?```", reply, maxsplit=1, flags=re.S)
            expl = parts[1].strip() if len(parts) > 1 else ""
            res = run_thee(code + "\n" + probe)
            out = res["stdout"].strip()
            verdict = "correct" if res["ok"] and out.splitlines()[-1:] == [expected] else ("wrong" if res["ok"] else "failed")
            demos.append({"question": q, "code": code, "probe": probe, "expected": expected, "output": out,
                          "error": res["stderr"], "explanation": expl, "verdict": verdict, "attempts": 1})
        else:
            r = ask(a.model, q, log=lambda s: print(s, file=sys.stderr))
            verdict = "verified" if r["verified"] else ("ran" if r.get("ran") else "failed")
            demos.append({"question": q, "code": r["code"], "output": r["output"], "error": r["error"],
                          "explanation": r["explanation"], "verdict": verdict, "attempts": r["attempts"]})
        print(f"{verdict:9s} {q[:40]}", file=sys.stderr)

    blocked = run_thee('நா தகவல் = read_file("/etc/passwd")\nமூச்சு தகவல்')
    roman = 'thee kootu(a, b) {\n    kanal a + b\n}\nmoochhu kootu(2, 3)'
    tamil = convert(roman, "tamil")
    conv = {"roman": roman, "tamil": tamil, "output": run_thee(tamil)["stdout"].strip()}

    score = None
    if a.score_file and os.path.exists(a.score_file):
        rows = read_jsonl(a.score_file)
        score = round(100 * sum(r["pass1"] for r in rows) / len(rows), 1)

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"demos": demos, "sandbox": {"code": 'நா தகவல் = read_file("/etc/passwd")',
                                                "error": blocked["stderr"]},
                   "convert": conv, "score_v2": score}, f, ensure_ascii=False, indent=2)
    print(f"saved {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
