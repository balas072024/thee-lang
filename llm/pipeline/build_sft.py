# -*- coding: utf-8 -*-
"""Turn verified data into chat-format training files (train.jsonl / valid.jsonl).

Inputs (any that exist):
  llm/data/verified.jsonl   from translate.py
  llm/data/repairs.jsonl    "here's my broken code + error, fix it" pairs from translate.py
  llm/seed/lessons.jsonl    hand-written tutor lessons

Each verified task becomes several examples:
  * Tamil request → romanized code + Tamil explanation
  * Tamil request asking for Tamil keywords → Tamil-script code + explanation
  * English request → code
  * "convert this Python to THEE" → code
Benchmark tasks are removed (by function name and near-duplicate prompt) so scores stay honest.

Output format is {"messages": [...]}, which mlx_lm.lora, TRL and Unsloth all read.

  python3 llm/pipeline/build_sft.py
"""
import argparse
import difflib
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LLM = os.path.dirname(HERE)
sys.path.insert(0, LLM)
sys.path.insert(0, HERE)
from common import read_jsonl, run_with_tests, write_jsonl  # noqa: E402
from prompts import SYSTEM_TUTOR  # noqa: E402
from tamil_script import convert  # noqa: E402


def _msgs(user, assistant):
    return {"messages": [{"role": "system", "content": SYSTEM_TUTOR},
                         {"role": "user", "content": user},
                         {"role": "assistant", "content": assistant}]}


def _answer(code, explain):
    return f"```thee\n{code}\n```" + (f"\n\n{explain}" if explain else "")


def load_benchmark():
    p = os.path.join(LLM, "benchmark", "tasks.jsonl")
    return read_jsonl(p) if os.path.exists(p) else []


def is_contaminated(row, bench):
    fn = (row.get("fn") or "").lower()
    en = (row.get("prompt_en") or "").lower()
    for b in bench:
        if fn and fn == b["fn"].lower():
            return True
        if en and difflib.SequenceMatcher(None, en, b["prompt_en"].lower()).ratio() > 0.85:
            return True
    return False


def examples_for_task(r, rng):
    out = []
    code, expl = r["thee"], r.get("explain_ta", "")
    fn = r.get("fn") or "the function"
    if r.get("prompt_ta"):
        out.append(_msgs(f"{r['prompt_ta']}\nFunction பேரு `{fn}`.", _answer(code, expl)))
        tamil_code = convert(code, "tamil")
        if run_with_tests(tamil_code, r["tests"])["passed"]:  # keep only if it still runs
            out.append(_msgs(f"{r['prompt_ta']}\nTamil keywords-ல எழுதுங்க. Function பேரு `{fn}`.",
                             _answer(tamil_code, expl)))
    out.append(_msgs(f"{r['prompt_en']}\nWrite it in THEE. Name the function `{fn}`.", _answer(code, "")))
    if r.get("python") and rng.random() < 0.5:
        out.append(_msgs(f"இந்த Python code-ஐ THEE-ஆ மாத்துங்க:\n```python\n{r['python']}\n```",
                         _answer(code, expl)))
    return out


def examples_for_repair(r):
    return [_msgs(f"இந்த THEE code-ல error வருது:\n```thee\n{r['bad_code']}\n```\nError:\n```\n{r['error']}\n```\n"
                  f"Task: {r['prompt_en']}\nசரி பண்ணி குடுங்க.",
                  _answer(r["fixed_code"], "இது தான் சரியான version. மேல இருக்கிற error message எந்த line-ல பிரச்சனைன்னு காட்டுது, அத மாத்தியிருக்கேன்."))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=os.path.join(LLM, "data"))
    ap.add_argument("--valid-frac", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--lesson-repeat", type=int, default=3, help="lessons are few, so repeat them")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    bench = load_benchmark()

    verified_p = os.path.join(a.data_dir, "verified.jsonl")
    repairs_p = os.path.join(a.data_dir, "repairs.jsonl")
    lessons_p = os.path.join(LLM, "seed", "lessons.jsonl")
    verified = read_jsonl(verified_p) if os.path.exists(verified_p) else []
    repairs = read_jsonl(repairs_p) if os.path.exists(repairs_p) else []
    lessons = read_jsonl(lessons_p) if os.path.exists(lessons_p) else []

    kept = [r for r in verified if not is_contaminated(r, bench)]
    rows, groups = [], []  # split by source task so variants of one task stay together
    for r in kept:
        groups.append(examples_for_task(r, rng))
    for r in repairs:
        m = re.search(r"\b(?:thee|தீ)\s+([^\s(]+)\s*\(", r.get("fixed_code", ""))
        r.setdefault("fn", m.group(1) if m else "")
        if not is_contaminated(r, bench):
            groups.append(examples_for_repair(r))
    lesson_rows = [_msgs(l["question_ta"], l["answer_ta"]) for l in lessons]

    rng.shuffle(groups)
    n_valid = max(1, int(len(groups) * a.valid_frac)) if len(groups) > 10 else 0
    valid = [ex for g in groups[:n_valid] for ex in g]
    train = [ex for g in groups[n_valid:] for ex in g] + lesson_rows * a.lesson_repeat
    if not valid:  # tiny data: still give the trainer a validation file
        valid = lesson_rows[:3] or train[:1]
    rng.shuffle(train)

    write_jsonl(os.path.join(a.data_dir, "train.jsonl"), train)
    write_jsonl(os.path.join(a.data_dir, "valid.jsonl"), valid)
    print(f"verified tasks: {len(verified)} ({len(verified) - len(kept)} removed as benchmark overlap)")
    print(f"repairs: {len(repairs)}, lessons: {len(lessons)} (x{a.lesson_repeat})")
    print(f"train: {len(train)} examples, valid: {len(valid)} → {a.data_dir}")


if __name__ == "__main__":
    main()
