#!/usr/bin/env python3
"""Check available Google AI models."""
import os
from dotenv import load_dotenv
import google.generativeai as genai  # type: ignore

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: No GOOGLE_API_KEY found")
    exit(1)

genai.configure(api_key=api_key)

print("Available models for generateContent:")
print("-" * 60)
for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(f"- {model.name}")
        print(f"  Display name: {model.display_name}")
        print(f"  Description: {model.description[:80]}...")
        print()
