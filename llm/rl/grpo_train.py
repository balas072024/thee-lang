# -*- coding: utf-8 -*-
"""Phase 5 — reinforcement learning with the THEE interpreter as the judge (GRPO).

Starts from the phase-3 model (llm/train/fused). For each prompt the model writes several
answers; each is run against the task's tests in sandbox mode. Reward is simple on purpose:
1.0 if every test passes, 0.0 otherwise (no style or length bonuses, which invite reward hacking).

Two kinds of prompts, mixed:
  * write:  a Tamil or English task → code
  * repair: broken THEE code + its real error message → fixed code (teaches reading errors,
            which is what a tutor does with a student)

Needs an NVIDIA GPU (TRL GRPO is impractical on a Mac):
  pip install "trl>=0.14" "peft>=0.13" "transformers>=4.46" datasets accelerate
  python3 llm/rl/grpo_train.py                  # LoRA on top of llm/train/fused
  python3 llm/rl/grpo_train.py --use-vllm       # much faster generation if vLLM is installed
Writes the RL-tuned merged model to llm/rl/fused-rl; package it with
  FUSED=llm/rl/fused-rl bash llm/package/build_ollama.sh
"""
import argparse
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
LLM = os.path.dirname(HERE)
ROOT = os.path.dirname(LLM)
sys.path.insert(0, LLM)
sys.path.insert(0, os.path.join(LLM, "pipeline"))
from common import extract_code, read_jsonl, run_with_tests  # noqa: E402
from prompts import SYSTEM_TUTOR  # noqa: E402
from build_sft import is_contaminated, load_benchmark  # noqa: E402


def build_prompts(data_dir, repair_share, seed):
    """Rows of {prompt: [messages], tests: [...], kind}. Benchmark tasks are excluded."""
    rng = random.Random(seed)
    bench = load_benchmark()
    vpath, rpath = os.path.join(data_dir, "verified.jsonl"), os.path.join(data_dir, "repairs.jsonl")
    verified = [r for r in (read_jsonl(vpath) if os.path.exists(vpath) else []) if not is_contaminated(r, bench)]
    by_id = {r["id"]: r for r in verified}
    rows = []
    for r in verified:
        ask = r["prompt_ta"] if r.get("prompt_ta") and rng.random() < 0.7 else r["prompt_en"]
        user = f"{ask}\nFunction பேரு `{r['fn']}`. முழு THEE code-ஐ ```thee block-ல குடு."
        rows.append({"prompt": [{"role": "system", "content": SYSTEM_TUTOR}, {"role": "user", "content": user}],
                     "tests": r["tests"], "kind": "write"})
    repairs = [p for p in (read_jsonl(rpath) if os.path.exists(rpath) else []) if p["id"] in by_id]
    rng.shuffle(repairs)
    for p in repairs[: int(len(rows) * repair_share)]:
        user = (f"இந்த THEE code-ல error வருது:\n```thee\n{p['bad_code']}\n```\nError:\n```\n{p['error']}\n```\n"
                f"Task: {p['prompt_en']}\nசரி பண்ணி முழு code-ஐ குடுங்க.")
        rows.append({"prompt": [{"role": "system", "content": SYSTEM_TUTOR}, {"role": "user", "content": user}],
                     "tests": by_id[p["id"]]["tests"], "kind": "repair"})
    rng.shuffle(rows)
    return rows


def _text(completion):
    if isinstance(completion, list):  # conversational: [{"role": "assistant", "content": ...}]
        return completion[-1]["content"] if completion else ""
    return completion


def tests_pass_reward(prompts, completions, tests, **kwargs):
    """1.0 if the code passes every test in the sandbox, else 0.0."""
    def score(pair):
        comp, t = pair
        code = extract_code(_text(comp))
        return 1.0 if code and run_with_tests(code, t)["passed"] else 0.0
    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(score, zip(completions, tests)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=os.path.join(LLM, "train", "fused"))
    ap.add_argument("--data-dir", default=os.path.join(LLM, "data"))
    ap.add_argument("--out", default=os.path.join(HERE, "adapters-rl"))
    ap.add_argument("--merged", default=os.path.join(HERE, "fused-rl"))
    ap.add_argument("--repair-share", type=float, default=0.3, help="repair prompts per write prompt")
    ap.add_argument("--generations", type=int, default=8, help="answers per prompt (the GRPO group)")
    ap.add_argument("--steps", type=int, default=500)
    ap.add_argument("--lr", type=float, default=5e-6)
    ap.add_argument("--use-vllm", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="build prompts and test the reward, no training")
    a = ap.parse_args()

    rows = build_prompts(a.data_dir, a.repair_share, seed=7)
    print(f"{len(rows)} RL prompts ({sum(r['kind'] == 'repair' for r in rows)} repair)")
    if a.dry_run:
        return
    if not rows:
        sys.exit("No prompts — run phase 2 (translate.py) first.")

    import torch
    import transformers
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer

    tok = AutoTokenizer.from_pretrained(a.model)
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    dtype_kw = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(
        a.model, **{dtype_kw: torch.bfloat16 if use_bf16 else torch.float32},
        device_map="auto" if torch.cuda.is_available() else None)
    ds = Dataset.from_list([{"prompt": r["prompt"], "tests": r["tests"]} for r in rows])
    cfg = GRPOConfig(
        output_dir=a.out, learning_rate=a.lr, max_steps=a.steps, bf16=use_bf16,
        per_device_train_batch_size=a.generations, num_generations=a.generations,
        gradient_accumulation_steps=2, max_completion_length=768,
        temperature=0.8, beta=0.04, logging_steps=10, save_steps=100, save_total_limit=2,
        use_vllm=a.use_vllm, report_to="none", seed=7,
    )
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    trainer = GRPOTrainer(model=model, reward_funcs=tests_pass_reward, args=cfg, train_dataset=ds,
                          processing_class=tok, peft_config=lora)
    trainer.train()
    trainer.save_model(a.out)
    merged = trainer.model.merge_and_unload()
    merged.save_pretrained(a.merged, safe_serialization=True)
    tok.save_pretrained(a.merged)
    print(f"Done → {a.merged}. Score: serve it, then run llm/benchmark/run_benchmark.py; "
          "keep it only if pass@1 beats the phase-3 model.")


if __name__ == "__main__":
    main()
