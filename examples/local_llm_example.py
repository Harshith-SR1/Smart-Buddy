"""
Lightweight local LLM example using Hugging Face Transformers (CPU-only).
Run this after installing dependencies with `scripts/install_local_llm.ps1`.

Usage:
  # activate your venv
  & ".\.venv\Scripts\Activate.ps1"
  # install deps (only once)
  powershell -ExecutionPolicy Bypass -File .\scripts\install_local_llm.ps1
  # run the example
  python .\examples\local_llm_example.py

This example uses `distilgpt2` which is small and runs on CPU. It's not instruction-tuned
like Gemini, but it's free to run locally for demos and testing.
"""

from transformers import pipeline


def main():
    print(
        "Loading local text-generation model (distilgpt2). This may download weights..."
    )
    generator = pipeline("text-generation", model="distilgpt2")
    prompt = (
        "Hello Smart Buddy, please summarize the weather for today in one sentence."
    )
    print("Prompt:\n", prompt)
    out = generator(prompt, max_length=80, num_return_sequences=1)
    print("\nGenerated:\n", out[0]["generated_text"])


if __name__ == "__main__":
    main()
