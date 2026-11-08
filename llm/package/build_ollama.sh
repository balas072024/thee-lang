#!/usr/bin/env bash
# Phase 4: fused model → GGUF → Ollama model "thee" (Q8_0, ~1.6 GB for 1.5B; QUANT=q4_K_M for ~1 GB).
#   bash llm/package/build_ollama.sh
#   OLLAMA_USER=yourname bash llm/package/build_ollama.sh   # also push to ollama.com as yourname/thee
set -euo pipefail
cd "$(dirname "$0")/../.."

FUSED=${FUSED:-llm/train/fused}
OUT=llm/package
QUANT=${QUANT:-q8_0}

[ -d "$FUSED" ] || { echo "No $FUSED — run llm/train/train_mac.sh (or train_gpu.py) first"; exit 1; }
command -v ollama >/dev/null || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }

# 1. llama.cpp's converter (Python only, nothing to compile)
if [ ! -d "$OUT/llama.cpp" ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$OUT/llama.cpp"
fi
# The converter pins older library versions, so it gets its own environment
# (installing them into the main one breaks datasets/mlx-lm).
REQ="$OUT/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt"
CONV_PY="$OUT/.venv-convert/bin/python"
if [ ! -x "$CONV_PY" ]; then
  if command -v uv >/dev/null; then uv venv --python 3.12 "$OUT/.venv-convert" && uv pip install --python "$CONV_PY" -r "$REQ"
  else python3 -m venv "$OUT/.venv-convert" && "$CONV_PY" -m pip install --quiet -r "$REQ"; fi
fi

# MLX saves extra_special_tokens as a list; the converter's transformers expects a dict.
python3 - "$FUSED/tokenizer_config.json" <<'PY'
import json, sys
p = sys.argv[1]; c = json.load(open(p))
if isinstance(c.get("extra_special_tokens"), list):
    c.pop("extra_special_tokens"); json.dump(c, open(p, "w"), ensure_ascii=False, indent=2)
PY

# 2. HF safetensors → GGUF (f16)
echo "▶ Converting to GGUF"
"$CONV_PY" "$OUT/llama.cpp/convert_hf_to_gguf.py" "$FUSED" --outfile "$OUT/thee-f16.gguf" --outtype f16

# 3. Quantize (Ollama can't quantize a GGUF import, so llama.cpp does it: brew install llama.cpp)
GGUF=thee-f16.gguf
if command -v llama-quantize >/dev/null; then
  Q=$(echo "$QUANT" | tr '[:lower:]' '[:upper:]')
  echo "▶ Quantizing to $Q"
  llama-quantize "$OUT/thee-f16.gguf" "$OUT/thee-$QUANT.gguf" "$Q"
  GGUF=thee-$QUANT.gguf
else
  echo "llama-quantize not found (brew install llama.cpp) — using the unquantized f16 model"
fi

# 4. Modelfile with the Tamil tutor system prompt, then the Ollama model
python3 llm/package/make_modelfile.py --gguf "$GGUF" > "$OUT/Modelfile"
echo "▶ Creating Ollama model 'thee' from $GGUF"
(cd "$OUT" && ollama create thee -f Modelfile)
ollama run thee "ஒரு number இரட்டைப்படையா-ன்னு check பண்ற function எழுதுங்க" || true

# 5. Score the packaged model
python3 llm/benchmark/run_benchmark.py --model ollama:thee --system none

# 6. Optional: publish so anyone can `ollama pull <you>/thee`
if [ -n "${OLLAMA_USER:-}" ]; then
  ollama cp thee "$OLLAMA_USER/thee"
  ollama push "$OLLAMA_USER/thee"
  echo "✓ Published: ollama pull $OLLAMA_USER/thee"
fi

echo "✓ Done:  ollama run thee"
