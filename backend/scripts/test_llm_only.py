import sys

import torch

from api_server import load_model


def _get_model_and_tokenizer():
  """Load the LoRA-finetuned base model once."""
  model, tokenizer = load_model()
  device = next(model.parameters()).device
  return model, tokenizer, device


def ask(prompt: str, max_new_tokens: int = 256) -> None:
  """Run a single LLM-only generation and print the result."""
  model, tokenizer, device = _get_model_and_tokenizer()

  inputs = tokenizer(prompt, return_tensors="pt").to(device)
  with torch.no_grad():
    outputs = model.generate(
      **inputs,
      max_new_tokens=max_new_tokens,
      do_sample=True,
      temperature=0.7,
      top_p=0.9,
      pad_token_id=tokenizer.eos_token_id,
    )

  text = tokenizer.decode(outputs[0], skip_special_tokens=True)
  print("\n=== PROMPT ===")
  print(prompt)
  print("\n=== ANSWER ===")
  print(text)
  print("\n" + "=" * 60 + "\n")


def main() -> None:
  if len(sys.argv) > 1:
    # One-shot usage: python scripts/test_llm_only.py "your question"
    prompt = " ".join(sys.argv[1:]).strip()
    if prompt:
      ask(prompt)
    return

  # Interactive REPL mode
  print("LLM-only test (no RAG). Type a question, or 'exit' to quit.")
  while True:
    try:
      q = input(">> ").strip()
    except EOFError:
      break
    if not q or q.lower() in {"exit", "quit"}:
      break
    ask(q)


if __name__ == "__main__":
  main()

