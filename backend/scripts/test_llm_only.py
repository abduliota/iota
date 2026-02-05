import os
import sys

import torch

# Ensure the backend root (one level up) is on sys.path so we can import api_server
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
  sys.path.insert(0, BACKEND_DIR)

from api_server import load_model

# Cache model/tokenizer globally to avoid reloading on every question
_model_cache = None
_tokenizer_cache = None
_device_cache = None


def _get_model_and_tokenizer():
  """Load the LoRA-finetuned base model once and cache it."""
  global _model_cache, _tokenizer_cache, _device_cache
  if _model_cache is None:
    _model_cache, _tokenizer_cache = load_model()
    _device_cache = next(_model_cache.parameters()).device
  return _model_cache, _tokenizer_cache, _device_cache


def ask(prompt: str, max_new_tokens: int = 384) -> None:
  """Run a single LLM-only generation with banking/regulatory domain constraints."""
  model, tokenizer, device = _get_model_and_tokenizer()

  # System prompt that constrains answers to banking/regulatory domain
  system_prompt = (
    "You are a regulatory AI assistant specializing in Saudi Arabian banking and financial regulations. "
    "You answer questions about SAMA (Saudi Central Bank), CMA (Capital Market Authority), banking sector rules, "
    "licensing provisions, governance, compliance, and related regulatory topics.\n\n"
    "Rules:\n"
    "- Answer ONLY questions related to banking, finance, and regulatory matters in Saudi Arabia.\n"
    "- If asked about non-regulatory topics, politely redirect: 'I specialize in Saudi banking and financial regulations. "
    "Could you rephrase your question about SAMA, CMA, or banking rules?'\n"
    "- For acronyms like 'SAMA', always interpret them in the banking/regulatory context (Saudi Central Bank).\n"
    "- Be conversational, clear, and professional. Use your knowledge from regulatory training data.\n"
    "- If you don't know something specific, say so rather than guessing."
  )

  # Format as chat messages using the tokenizer's chat template (like api_server does)
  messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt},
  ]
  
  # Apply chat template to format the prompt correctly
  formatted_prompt = tokenizer.apply_chat_template(
    messages, 
    tokenize=False, 
    add_generation_prompt=True
  )

  # Tokenize and generate
  inputs = tokenizer(
    formatted_prompt,
    return_tensors="pt",
    truncation=True,
    max_length=2048,
  ).to(device)
  
  with torch.no_grad():
    outputs = model.generate(
      **inputs,
      max_new_tokens=max_new_tokens,
      do_sample=False,
      temperature=0.3,
      pad_token_id=tokenizer.eos_token_id,
    )

  # Extract only the assistant's response (skip the prompt part)
  prompt_len = inputs["input_ids"].shape[1]
  response = tokenizer.decode(
    outputs[0][prompt_len:], 
    skip_special_tokens=True
  )
  
  print("\n=== PROMPT ===")
  print(prompt)
  print("\n=== ANSWER ===")
  print(response.strip())
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

