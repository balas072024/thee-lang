# -*- coding: utf-8 -*-
"""LoRA training with quality gates: stop early when the model isn't getting better.

Validation loss alone misled us (v2: best val loss, worst model). So while mlx_lm trains, this
script scores each saved checkpoint at the gate steps on a quick set of benchmark tasks
(function only: the model's own assert_eq lines are removed before the hidden tests run),
and stops training when:
  * a checkpoint at or after --min-step scores below --floor (e.g. the current best model), or
  * --patience gates in a row bring no improvement.
At the end the best-scoring checkpoint is fused to --out. The full benchmark is still the final word.

  python3 llm/train/train_gated.py --data llm/data/v3 --out llm/train/fused-v3 \\
      --iters 4000 --lr 5e-5 --floor 7      # v1 passes 7 of the 15 quick tasks
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LLM = os.path.dirname(HERE)
ROOT = os.path.dirname(LLM)
sys.path.insert(0, LLM)
from common import extract_code, read_jsonl, run_with_tests  # noqa: E402
from prompts import SYSTEM_TUTOR, task_prompt  # noqa: E402

_OWN_CHECKS = re.compile(r"(?m)^\s*assert_eq\(.*$")


def quick_score(base, adapter_dir, tasks, max_tokens=350):
    """Pass count on the quick tasks for base model + one LoRA adapter (greedy decoding)."""
    from mlx_lm import generate, load
    model, tok = load(base, adapter_path=adapter_dir)
    passed = 0
    for t in tasks:
        msgs = [{"role": "system", "content": SYSTEM_TUTOR}, {"role": "user", "content": task_prompt(t, "ta")}]
        prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        code = _OWN_CHECKS.sub("", extract_code(generate(model, tok, prompt=prompt, max_tokens=max_tokens,
                                                          verbose=False)))
        passed += run_with_tests(code, t["tests"])["passed"]
    del model
    return passed


def quick_score_isolated(base, adapter_dir, n_quick):
    """Score in a separate process so all of its GPU memory is returned when it exits."""
    out = subprocess.run([sys.executable, os.path.abspath(__file__), "--score-only", base, adapter_dir, str(n_quick)],
                         capture_output=True, text=True, cwd=ROOT)
    m = re.search(r"SCORE=(\d+)", out.stdout)
    if not m:
        print(out.stderr[-1500:], flush=True)
        raise RuntimeError("gate scoring failed")
    return int(m.group(1))


def snapshot(adapters, step):
    """Copy one saved checkpoint into its own adapter folder (what mlx_lm.load expects)."""
    import shutil
    src = os.path.join(adapters, f"{step:07d}_adapters.safetensors")
    dst = f"{adapters}-step{step}"
    os.makedirs(dst, exist_ok=True)
    shutil.copy(os.path.join(adapters, "adapter_config.json"), dst)
    shutil.copy(src, os.path.join(dst, "adapters.safetensors"))
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.join(HERE, "mlx_lora.yaml"))
    ap.add_argument("--data", required=True, help="folder with train.jsonl / valid.jsonl")
    ap.add_argument("--adapters", default=os.path.join(HERE, "adapters-gated"))
    ap.add_argument("--out", required=True, help="where to fuse the best checkpoint")
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--gate-every", type=int, default=200)
    ap.add_argument("--min-step", type=int, default=200, help="first gate that may stop training")
    ap.add_argument("--floor", type=int, default=0, help="stop if a gate scores below this (quick tasks passed)")
    ap.add_argument("--patience", type=int, default=3, help="stop after this many gates without improvement")
    ap.add_argument("--quick", type=int, default=15, help="number of quick benchmark tasks")
    a = ap.parse_args()

    import yaml
    cfg = yaml.safe_load(open(a.config))
    base = cfg["model"]
    cfg.update({"data": a.data, "iters": a.iters, "learning_rate": a.lr, "adapter_path": a.adapters,
                "save_every": a.gate_every, "steps_per_eval": a.gate_every})
    run_cfg = os.path.join(HERE, "gated_run.yaml")
    yaml.safe_dump(cfg, open(run_cfg, "w"))
    tasks = read_jsonl(os.path.join(LLM, "benchmark", "tasks.jsonl"))[:a.quick]
    log_path = a.adapters + "-gates.jsonl"
    os.makedirs(a.adapters, exist_ok=True)

    print(f"▶ training {base} on {a.data}: {a.iters} iters, lr {a.lr}, gate every {a.gate_every}, "
          f"floor {a.floor}/{a.quick}, patience {a.patience}", flush=True)
    proc = subprocess.Popen([sys.executable, "-m", "mlx_lm", "lora", "--config", run_cfg], cwd=ROOT)

    best_step, best, since_best, gates, reason = None, -1, 0, [], "finished"
    next_gate = a.gate_every
    while True:
        ckpt = os.path.join(a.adapters, f"{next_gate:07d}_adapters.safetensors")
        if os.path.exists(ckpt) and time.time() - os.path.getmtime(ckpt) > 5:  # fully written
            # Pause training while the gate generates: two models on the GPU at once ran out of
            # Metal memory (v4). SIGSTOP keeps its state; SIGCONT resumes exactly where it was.
            import gc, signal
            proc.send_signal(signal.SIGSTOP)
            try:
                score = quick_score_isolated(base, snapshot(a.adapters, next_gate), len(tasks))
            finally:
                gc.collect()
                try:
                    import mlx.core as mx
                    (getattr(mx, "clear_cache", None) or mx.metal.clear_cache)()
                except Exception:
                    pass
                proc.send_signal(signal.SIGCONT)
            gates.append({"step": next_gate, "passed": score, "of": len(tasks)})
            with open(log_path, "a") as f:
                f.write(json.dumps(gates[-1]) + "\n")
            improved = score > best
            if improved:
                best, best_step, since_best = score, next_gate, 0
            else:
                since_best += 1
            print(f"◆ gate step {next_gate}: {score}/{len(tasks)}"
                  + ("  (best so far)" if improved else f"  (best {best} at step {best_step})"), flush=True)
            if next_gate >= a.min_step and score < a.floor:
                reason = f"step {next_gate} scored {score} < floor {a.floor}"
            elif since_best >= a.patience:
                reason = f"no improvement for {a.patience} gates"
            if reason != "finished":
                proc.send_signal(__import__('signal').SIGCONT)
                proc.terminate()
                proc.wait()
                break
            next_gate += a.gate_every
            continue
        if proc.poll() is not None:  # training ended; score any last checkpoint we haven't seen
            if not os.path.exists(ckpt):
                break
            continue
        time.sleep(10)

    print(f"■ stopped: {reason}. Gates: " + ", ".join(f"{g['step']}→{g['passed']}" for g in gates), flush=True)
    if best_step is None:
        sys.exit("no checkpoint was scored")
    if best < a.floor:
        print(f"✗ best checkpoint ({best}/{len(tasks)} at step {best_step}) is below the floor "
              f"({a.floor}); not fusing — keep the current model.", flush=True)
        sys.exit(2)
    subprocess.run(["bash", os.path.join(HERE, "pick_checkpoint.sh"), str(best_step), a.adapters, a.out],
                   check=True, cwd=ROOT)
    print(f"✓ fused step {best_step} ({best}/{len(tasks)}) → {a.out}. Next: full benchmark.", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--score-only":
        _b, _ad, _n = sys.argv[2], sys.argv[3], int(sys.argv[4])
        print(f"SCORE={quick_score(_b, _ad, read_jsonl(os.path.join(LLM, 'benchmark', 'tasks.jsonl'))[:_n])}")
        sys.exit(0)
    main()
