#!/usr/bin/env bash
# Fuse a saved LoRA checkpoint (e.g. the one with the lowest val loss) instead of the last one.
#   bash llm/train/pick_checkpoint.sh 200        # uses llm/train/adapters/0000200_adapters.safetensors
set -euo pipefail
cd "$(dirname "$0")/../.."
STEP=$(printf "%07d" "$1")
SRC=llm/train/adapters
DST=llm/train/adapters-$1
BASE=$(grep '^model:' llm/train/mlx_lora.yaml | sed 's/model: *"\(.*\)"/\1/')
mkdir -p "$DST"
cp "$SRC/adapter_config.json" "$DST/"
cp "$SRC/${STEP}_adapters.safetensors" "$DST/adapters.safetensors"
python3 -m mlx_lm fuse --model "$BASE" --adapter-path "$DST" --save-path llm/train/fused
echo "✓ llm/train/fused now holds checkpoint $1"
