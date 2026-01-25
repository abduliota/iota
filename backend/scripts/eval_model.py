import os
import json
from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

"""
Minimal eval:
- Loads base + LoRA adapter from backend/models/lora_adapter/
- Runs on backend/datasets/test.jsonl
- Saves a small sample of predictions to backend/datasets/eval_samples.jsonl
"""

MODEL_NAME = os.environ.get("BASE_MODEL_NAME", "Qwen/Qwen2-7B-Instruct")
ADAPTER_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "lora_adapter")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
OUT_PATH = os.path.join(DATA_DIR, "eval_samples.jsonl")


def load_test(path: str) -> List[Dict]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            q = obj.get("question", "").strip()
            a = obj.get("answer", "").strip()
            if q:
                items.append({"question": q, "answer": a})
    return items


def extract_assistant_response(full_output: str) -> str:
    """Extract only the assistant's response from the full output."""
    # The model outputs: "system\n...\nuser\n...\nassistant\n[answer]"
    if "assistant" in full_output.lower():
        # Split by "assistant" and take the last part
        parts = full_output.split("assistant")
        if len(parts) > 1:
            answer = parts[-1].strip()
            # Remove any remaining system/user prompts
            if "\nuser\n" in answer:
                answer = answer.split("\nuser\n")[0]
            if "\nsystem\n" in answer:
                answer = answer.split("\nsystem\n")[0]
            return answer.strip()
    return full_output.strip()


def main():
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR, use_fast=False)
    tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,
    )
    model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    model.config.pad_token_id = tokenizer.pad_token_id

    test_path = os.path.join(DATA_DIR, "test.jsonl")
    data = load_test(test_path)[:50]  # sample 50 for quick eval

    out = []
    for item in data:
        messages = [
            {"role": "system", "content": "You are a helpful assistant for KSA regulatory compliance."},
            {"role": "user", "content": item["question"]},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        enc = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=1024,
        ).to(model.device)
        with torch.no_grad():
            gen = model.generate(
                **enc,
                max_new_tokens=128,
                temperature=0.3,
                do_sample=False,
            )
        output = tokenizer.decode(gen[0], skip_special_tokens=True)
        # Extract only assistant response
        clean_output = extract_assistant_response(output)
        out.append({"question": item["question"], "reference": item["answer"], "prediction": clean_output})

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Saved eval samples to {OUT_PATH}")


if __name__ == "__main__":
    main()
