#!/usr/bin/env bash
# Phase 4: fused model → GGUF → Ollama model "thee" (Q4_K_M, ~1 GB for 1.5B).
#   bash llm/package/build_ollama.sh
#   OLLAMA_USER=yourname bash llm/package/build_ollama.sh   # also push to ollama.com as yourname/thee
set -euo pipefail
cd "$(dirname "$0")/../.."

FUSED=${FUSED:-llm/train/fused}
OUT=llm/package
QUANT=${QUANT:-q4_K_M}

[ -d "$FUSED" ] || { echo "No $FUSED — run llm/train/train_mac.sh (or train_gpu.py) first"; exit 1; }
command -v ollama >/dev/null || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }

# 1. llama.cpp's converter (Python only, nothing to compile)
if [ ! -d "$OUT/llama.cpp" ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$OUT/llama.cpp"
fi
python3 -m pip install --quiet -r "$OUT/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt"

# 2. HF safetensors → GGUF (f16)
echo "▶ Converting to GGUF"
python3 "$OUT/llama.cpp/convert_hf_to_gguf.py" "$FUSED" --outfile "$OUT/thee-f16.gguf" --outtype f16

# 3. Modelfile with the Tamil tutor system prompt
python3 llm/package/make_modelfile.py --gguf thee-f16.gguf > "$OUT/Modelfile"

# 4. Create the Ollama model; Ollama does the quantization itself
echo "▶ Creating Ollama model 'thee' ($QUANT)"
(cd "$OUT" && ollama create thee -f Modelfile --quantize "$QUANT")
ollama run thee "ஒரு number இரட்டைப்படையா-ன்னு check பண்ற function எழுதுங்க" || true

# 5. Score the packaged model
python3 llm/benchmark/run_benchmark.py --model ollama:thee

# 6. Optional: publish so anyone can `ollama pull <you>/thee`
if [ -n "${OLLAMA_USER:-}" ]; then
  ollama cp thee "$OLLAMA_USER/thee"
  ollama push "$OLLAMA_USER/thee"
  echo "✓ Published: ollama pull $OLLAMA_USER/thee"
fi

echo "✓ Done:  ollama run thee"
