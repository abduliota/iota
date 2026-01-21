import os
import json
import random
from typing import Set

"""
Clean and split Q&A dataset.
Input: backend/datasets/qa_raw.jsonl
Outputs:
  - backend/datasets/train.jsonl (80%)
  - backend/datasets/val.jsonl   (10%)
  - backend/datasets/test.jsonl  (10%)

Rules:
- Drop empty questions/answers
- Drop answers containing "Not found in the provided text."
- Drop duplicate questions (case-insensitive)
"""


def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "datasets")
    raw_path = os.path.join(base_dir, "qa_raw.jsonl")
    train_path = os.path.join(base_dir, "train.jsonl")
    val_path = os.path.join(base_dir, "val.jsonl")
    test_path = os.path.join(base_dir, "test.jsonl")

    records = []
    seen: Set[str] = set()
    drop_phrase = "not found in the provided text"

    for rec in load_jsonl(raw_path):
        q = rec.get("question", "").strip()
        a = rec.get("answer", "").strip()
        if not q or not a:
            continue
        if drop_phrase.lower() in a.lower():
            continue
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        records.append({"question": q, "answer": a, "language": rec.get("language"), "source": rec.get("source")})

    random.seed(42)
    random.shuffle(records)

    n = len(records)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    train = records[:n_train]
    val = records[n_train : n_train + n_val]
    test = records[n_train + n_val :]

    def write(path, items):
        with open(path, "w", encoding="utf-8") as f:
            for r in items:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    write(train_path, train)
    write(val_path, val)
    write(test_path, test)

    print(f"Total kept: {n}")
    print(f"train: {len(train)}, val: {len(val)}, test: {len(test)}")
    print(f"Written to:\n  {train_path}\n  {val_path}\n  {test_path}")


if __name__ == "__main__":
    main()
