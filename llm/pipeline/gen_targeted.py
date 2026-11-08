"""v4 data: Python tasks aimed at THEE v3's weak spots, every one checked by running it.

Weak spots come from the v3 benchmark failures: empty/edge inputs (len(m[0]) on []),
dict counting/grouping, off-by-one ranges (1..n), exact string output (joins, padding,
case conversion), nested lists, None/zero guards, small DP/stack/queue logic.
Output rows feed translate.py --source llm/data/targeted_py.jsonl (Python → THEE, verified).

  bash llm/with_anthropic_env.sh ~/Claude/manbalai/backend/.env \
    python3 llm/pipeline/gen_targeted.py --per-call 20 --rounds 3 --budget 6
"""
import argparse, json, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import api_cost, chat, read_jsonl  # noqa: E402

CATEGORIES = {
    "edge_empty": "functions that must handle empty lists/strings/dicts, single elements and zero correctly (e.g. sum of an empty matrix is 0, max of [] returns None)",
    "dict_count": "counting, grouping and merging with dicts (word counts, group by length/first letter, invert a dict, merge with sums), insertion order kept",
    "ranges": "loops with exact bounds: 1..n inclusive, evens/odds/multiples in a range, step ranges, reversed ranges, first/last n items",
    "string_exact": "exact string output: join with ', ' and ' and ', padding/masking (e.g. '****1234'), title/snake/camel case conversion, repeat patterns, formatting numbers",
    "nested": "nested lists: matrix sum/transpose/diagonal/row max, flatten, pairs, list of [name, score] records sorted by score then name",
    "guards": "None, zero and invalid-input guards: safe divide returns None, parse int or return default, clamp, validate age/ranges, return booleans exactly",
    "classic": "small classic algorithms: stack (balanced brackets), queue order, coin change count, pascal row, fibonacci list, prime list, gcd/lcm, binary search, running totals",
    "everyday_ta": "everyday Tamil Nadu style problems with plain ASCII data: auto fare by km slab, electricity bill slabs, GST bill total, exam grade, bus seat booking, cricket run rate",
}

SPEC = """Write {n} small, distinct Python programming tasks about: {topic}.
Rules:
- Each task is ONE top-level function using only builtins (no imports, no classes, no f-string format specs beyond {{x}}), 3-15 lines.
- Prefer plain loops, if/else, lists, dicts, strings. No lambda, no comprehensions with conditions nested twice, no generators, no recursion deeper than simple.
- 3-5 asserts each, at least one edge case (empty, zero, single item, boundary).
- Use a descriptive snake_case function name, unique across tasks.
Return ONLY a JSON list: [{{"text": "one-line task description", "code": "def ...", "tests": ["assert f(...) == ...", ...]}}]"""


def run_py(code, tests):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code + "\n" + "\n".join(tests) + "\n"); p = f.name
    try:
        r = subprocess.run([sys.executable, "-I", p], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.remove(p)


def one_call(args):
    cat, rnd, n, model = args
    try:
        txt = chat(model, [{"role": "user", "content": SPEC.format(n=n, topic=CATEGORIES[cat]) +
                            f"\n(Batch {rnd}: make these different from typical textbook examples.)"}], max_tokens=8000)
        m = re.search(r"\[.*\]", txt, re.S)
        return cat, rnd, json.loads(m.group(0)) if m else []
    except Exception as e:
        print("call failed", cat, rnd, e); return cat, rnd, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="anthropic:claude-sonnet-5-5")
    ap.add_argument("--per-call", type=int, default=20)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--budget", type=float, default=6.0)
    ap.add_argument("--out", default="llm/data/targeted_py.jsonl")
    a = ap.parse_args()
    bench = {t["fn"] for t in read_jsonl("llm/benchmark/tasks.jsonl")}  # decontaminate by name
    seen = set(); rows = []
    if os.path.exists(a.out):
        rows = list(read_jsonl(a.out)); seen = {r["fn"] for r in rows}
    jobs = [(c, r, a.per_call, a.model) for r in range(a.rounds) for c in CATEGORIES]
    with ThreadPoolExecutor(4) as ex:
        for cat, rnd, tasks in ex.map(lambda j: j if api_cost()[0] >= a.budget else one_call(j), jobs):
            if not isinstance(tasks, list): continue
            kept = 0
            for t in tasks:
                try:
                    fn = re.search(r"def\s+(\w+)", t["code"]).group(1)
                except Exception:
                    continue
                if fn in seen or fn in bench or not run_py(t["code"], t["tests"]):
                    continue
                seen.add(fn); kept += 1
                rows.append({"id": f"tg_{cat}_{len(rows):04d}", "fn": fn, "category": cat,
                             "text": t["text"], "code": t["code"], "tests": t["tests"]})
            print(f"{cat} r{rnd}: kept {kept}/{len(tasks)}  (${api_cost()[0]:.2f})", flush=True)
            with open(a.out, "w", encoding="utf-8") as f:
                for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"total {len(rows)} verified Python tasks → {a.out}; API ${api_cost()[0]:.2f}")


if __name__ == "__main__":
    main()
