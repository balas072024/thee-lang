#!/usr/bin/env bash
# Phase 3 on a Mac (Apple Silicon): LoRA fine-tune → fuse → score on the benchmark.
#   bash llm/train/train_mac.sh            # full run
#   SKIP_TRAIN=1 bash llm/train/train_mac.sh   # only fuse + evaluate existing adapters
set -euo pipefail
cd "$(dirname "$0")/../.."

BASE=$(grep '^model:' llm/train/mlx_lora.yaml | sed 's/model: *"\(.*\)"/\1/')
ADAPTERS=llm/train/adapters
FUSED=llm/train/fused

# Install mlx-lm only if it's missing (works with pip venvs and uv venvs)
python3 -c "import mlx_lm, yaml" 2>/dev/null || {
  if command -v uv >/dev/null; then uv pip install --python "$(command -v python3)" "mlx-lm>=0.21" pyyaml
  else python3 -m pip install --quiet --upgrade "mlx-lm>=0.21" pyyaml; fi
}

if [ ! -f llm/data/train.jsonl ]; then
  echo "No llm/data/train.jsonl yet — run phase 2 first:"
  echo "  python3 llm/pipeline/translate.py --source mbpp --model <strong model>"
  echo "  python3 llm/pipeline/build_sft.py"
  exit 1
fi

if [ -z "${SKIP_TRAIN:-}" ]; then
  echo "▶ Training LoRA on $BASE"
  python3 -m mlx_lm.lora --config llm/train/mlx_lora.yaml
fi

echo "▶ Fusing adapters into $FUSED"
python3 -m mlx_lm.fuse --model "$BASE" --adapter-path "$ADAPTERS" --save-path "$FUSED"

echo "▶ Scoring on the THEE-Tamil benchmark"
python3 -m mlx_lm.server --model "$FUSED" --port 8080 >/tmp/thee_mlx_server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do curl -s localhost:8080/v1/models >/dev/null && break; sleep 2; done
python3 llm/benchmark/run_benchmark.py --model "openai:$FUSED@http://localhost:8080/v1" --workers 1 --system tutor
python3 llm/benchmark/run_benchmark.py --model "openai:$FUSED@http://localhost:8080/v1" --workers 1 --lang en --system tutor

echo "✓ Done. Next: bash llm/package/build_ollama.sh"
