# THEE LLM — a small, offline Tamil coding tutor

A 1.5B model that writes THEE code and explains it in everyday spoken Tamil, packaged for Ollama.
Everything here is plain Python; run it from the repo root.

| Phase | What | Where it runs | Command |
|---|---|---|---|
| 1 | Python bridge + sandbox mode | anywhere | done — `thee --sandbox file.th` |
| 2 | Verified Python→THEE data | Mac (needs a strong model) | `python3 llm/pipeline/translate.py ...` |
| — | Benchmark (109 Tamil tasks) | anywhere | `python3 llm/benchmark/run_benchmark.py ...` |
| 3 | LoRA fine-tune | Mac (MLX) or GPU | `bash llm/train/train_mac.sh` |
| 4 | Ollama model + web playground | Mac | `bash llm/package/build_ollama.sh` |
| 5 | GRPO, interpreter as judge | NVIDIA GPU | `python3 llm/rl/grpo_train.py` |

## 0. Baseline first (10 minutes)

See how a general model does before training anything — this is the number to beat.

```bash
ollama pull qwen2.5-coder:1.5b
python3 llm/benchmark/run_benchmark.py --model ollama:qwen2.5-coder:1.5b --with-reference
```

## 2. Build the training data

A strong model translates MBPP's ~1,000 Python tasks; the THEE interpreter keeps only translations that pass the tests.

```bash
pip install datasets
# Anthropic API (best quality):
export ANTHROPIC_API_KEY=...
python3 llm/pipeline/translate.py --source mbpp --model anthropic:claude-sonnet-5-5
# or fully local (slower, lower yield):
python3 llm/pipeline/translate.py --source mbpp --model ollama:qwen2.5-coder:32b
python3 llm/pipeline/translate.py --source humaneval --model anthropic:claude-sonnet-5-5   # optional, +164 tasks

python3 llm/seed/build_lessons.py        # 25 hand-written tutor lessons (already verified)
python3 llm/pipeline/build_sft.py        # → llm/data/train.jsonl, valid.jsonl
```

`translate.py` can be stopped and restarted; finished tasks are skipped. Failed translations that were fixed on a retry are saved to `llm/data/repairs.jsonl` and become "fix this error" lessons.
Benchmark tasks are removed from training data automatically.

## 3. Fine-tune

```bash
bash llm/train/train_mac.sh               # M1 Max: roughly 1–2 hours for 1.5B
# or on a rented NVIDIA GPU:
python3 llm/train/train_gpu.py
```

Both write the merged model to `llm/train/fused`. The Mac script also scores it on the benchmark in Tamil and English.
For a stronger desktop model, set `model:` in `llm/train/mlx_lora.yaml` to `Qwen/Qwen2.5-Coder-3B-Instruct`.

## 4. Package and share

```bash
bash llm/package/build_ollama.sh                       # creates `thee` (Q4_K_M, ~1 GB)
ollama run thee "ஒரு list-ல பெரிய number கண்டுபிடிக்கிற function எழுதுங்க"
OLLAMA_USER=yourname bash llm/package/build_ollama.sh  # also publish: ollama pull yourname/thee
```

Web playground (no install, runs THEE in the browser with Pyodide, sandbox on):

```bash
python3 -m http.server 8000      # from the repo root, then open http://localhost:8000/playground/
python3 playground/build_playground.py   # single-file version for any static host
```

The playground's tutor box talks to Ollama on the same computer: start it with `OLLAMA_ORIGINS="*" ollama serve`.

## 5. Reinforcement learning (optional, GPU)

```bash
python3 llm/rl/grpo_train.py --use-vllm
FUSED=llm/rl/fused-rl bash llm/package/build_ollama.sh
```

Reward is 1 when the generated code passes every test in the sandbox, else 0. About 30% of prompts are "here is broken code and its error, fix it", so the model learns to read THEE errors. Keep the RL model only if its benchmark pass@1 beats phase 3.

## Files

- `THEE_REFERENCE.md` — the language guide given to models (every example in it is run and checked)
- `prompts.py` — tutor and coder system prompts (the Modelfile uses the same tutor prompt)
- `common.py` — sandboxed runner, model client (`ollama:`, `openai:<name>@<url>`, `anthropic:`), helpers
- `pipeline/tamil_script.py` — convert keywords between Tamil script and romanized
- `benchmark/build_tasks.py` — the 109 tasks; rebuilds `tasks.jsonl` and checks every reference solution
- `seed/build_lessons.py` — tutor lessons; rebuilds `lessons.jsonl` and checks every code block
