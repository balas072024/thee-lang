# -*- coding: utf-8 -*-
"""Phase 3 on an NVIDIA GPU (rented box, Colab): LoRA SFT with TRL + PEFT, then merge.

  pip install "trl>=0.12" "peft>=0.13" "transformers>=4.46" datasets accelerate
  python3 llm/train/train_gpu.py                       # 1.5B, ~20 min on one A10/L4 for ~3k examples
  python3 llm/train/train_gpu.py --model Qwen/Qwen2.5-Coder-3B-Instruct --epochs 3

Writes LoRA adapters to llm/train/adapters-gpu and a merged model to llm/train/fused
(the same folder the Mac script uses), ready for llm/package/build_ollama.sh.
"""
import argparse
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "llm", "data"))
    ap.add_argument("--out", default=os.path.join(ROOT, "llm", "train", "adapters-gpu"))
    ap.add_argument("--merged", default=os.path.join(ROOT, "llm", "train", "fused"))
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=2048)
    a = ap.parse_args()

    import torch
    import transformers
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    ds = load_dataset("json", data_files={"train": os.path.join(a.data_dir, "train.jsonl"),
                                          "validation": os.path.join(a.data_dir, "valid.jsonl")})
    # prompt/completion form: TRL then trains only on the reply (works with any chat template)
    ds = ds.map(lambda r: {"prompt": r["messages"][:-1], "completion": r["messages"][-1:]},
                remove_columns=["messages"])
    tok = AutoTokenizer.from_pretrained(a.model)
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    dtype_kw = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(
        a.model, **{dtype_kw: torch.bfloat16 if use_bf16 else torch.float32},
        device_map="auto" if torch.cuda.is_available() else None)

    cfg = SFTConfig(
        output_dir=a.out, num_train_epochs=a.epochs, learning_rate=a.lr,
        per_device_train_batch_size=a.batch, per_device_eval_batch_size=a.batch,
        gradient_accumulation_steps=1, lr_scheduler_type="cosine", warmup_steps=20,
        logging_steps=20, eval_strategy="steps", eval_steps=200, save_steps=200,
        save_total_limit=2, bf16=use_bf16, max_length=a.max_len,
        completion_only_loss=True,  # learn only the replies, like mask_prompt on the Mac
        report_to="none", seed=7,
    )
    lora = LoraConfig(r=a.rank, lora_alpha=a.rank * 2, lora_dropout=0.05, task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds["train"], eval_dataset=ds["validation"],
                         processing_class=tok, peft_config=lora)
    trainer.train()
    trainer.save_model(a.out)

    print(f"Merging LoRA into {a.merged}")
    merged = trainer.model.merge_and_unload()
    merged.save_pretrained(a.merged, safe_serialization=True)
    tok.save_pretrained(a.merged)
    print("Done. Score it:  vllm serve llm/train/fused  (or Ollama after build_ollama.sh), then run_benchmark.py")


if __name__ == "__main__":
    main()
