# -*- coding: utf-8 -*-
"""Write the Ollama Modelfile for the THEE tutor (system prompt kept in sync with llm/prompts.py).

  python3 llm/package/make_modelfile.py --gguf thee-f16.gguf > llm/package/Modelfile
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts import SYSTEM_TUTOR  # noqa: E402

# ChatML, the chat format Qwen2.5 models were trained on.
TEMPLATE = '''{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}
{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
'''


def modelfile(gguf):
    sys_prompt = SYSTEM_TUTOR.replace('"""', "'''")
    return f'''# THEE tutor — Tamil programming help, runs fully offline.
FROM ./{gguf}

TEMPLATE """{TEMPLATE}"""

SYSTEM """{sys_prompt}"""

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.15
PARAMETER num_predict 700
PARAMETER num_ctx 4096
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"

LICENSE """Model weights: fine-tuned from Qwen2.5-Coder (Apache License 2.0). THEE data and code: see the thee-lang repository."""
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", default="thee-f16.gguf")
    a = ap.parse_args()
    sys.stdout.write(modelfile(a.gguf))


if __name__ == "__main__":
    main()
