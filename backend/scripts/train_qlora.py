import os
import json
from dataclasses import dataclass
from typing import List, Dict

import torch
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


"""
Minimal QLoRA training script.
Assumes train/val/test JSONL created by prepare_qa_dataset.py (fields: question, answer).
Model: Qwen2-7B-Instruct (change MODEL_NAME if needed).
Saves adapter to backend/models/lora_adapter/
"""

MODEL_NAME = os.environ.get("BASE_MODEL_NAME", "Qwen/Qwen2-7B-Instruct")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "lora_adapter")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")


class QADataset(Dataset):
    def __init__(self, path: str, tokenizer, system_prompt: str):
        self.items: List[Dict] = []
        for line in open(path, "r", encoding="utf-8"):
            obj = json.loads(line)
            q = obj.get("question", "").strip()
            a = obj.get("answer", "").strip()
            if not q or not a:
                continue
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ]
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            self.items.append(text)

        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.items[idx],
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=1024,
        )
        input_ids = enc.input_ids[0]
        attention_mask = enc.attention_mask[0]
        labels = input_ids.clone()
        return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,
    )
    model = prepare_model_for_kbit_training(model)
    lora_cfg = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)

    system_prompt = "You are a helpful assistant for KSA regulatory compliance. Answer in the same language as the user."

    train_path = os.path.join(DATA_DIR, "train.jsonl")
    val_path = os.path.join(DATA_DIR, "val.jsonl")

    train_ds = QADataset(train_path, tokenizer, system_prompt)
    val_ds = QADataset(val_path, tokenizer, system_prompt)

    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=1,
        learning_rate=2e-4,
        logging_steps=20,
        evaluation_strategy="steps",
        eval_steps=200,
        save_steps=200,
        bf16=False,
        fp16=True,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
    )
    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Adapter saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
