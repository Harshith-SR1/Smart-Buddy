"""
Example to run local gpt4all binary from Python and get a response.
This example expects `models/gpt4all/gpt4all.exe` and a model file like `models/gpt4all/ggml-gpt4all-small.bin`.
It calls the binary via subprocess and prints the output.
"""

import os
import subprocess
import shlex

ROOT = os.path.dirname(os.path.dirname(__file__))
MODEL_DIR = os.path.join(ROOT, "models", "gpt4all")
BINARY = os.path.join(MODEL_DIR, "gpt4all.exe")
MODEL = None
# pick any file in MODEL_DIR starting with ggml- or ending with .bin
for f in os.listdir(MODEL_DIR) if os.path.exists(MODEL_DIR) else []:
    if f.startswith("ggml") or f.endswith(".bin") or f.endswith(".bin.gz"):
        MODEL = os.path.join(MODEL_DIR, f)
        break

if not os.path.exists(BINARY):
    print("gpt4all binary not found at", BINARY)
    print(
        "Run scripts/install_gpt4all.ps1 to download a binary and model (or add them manually)."
    )
    raise SystemExit(1)
if not MODEL or not os.path.exists(MODEL):
    print("Model file not found in", MODEL_DIR)
    print("Place a ggml model (.bin) in that directory or update the script model URL.")
    raise SystemExit(1)

prompt = "Hello Smart Buddy, summarize the benefits of running a local model in one sentence."
print("Using model:", MODEL)

# Construct command for gpt4all CLI - flags vary by build; this is a general example
cmd = f'"{BINARY}" --model "{MODEL}" --prompt "{prompt}" --n_predict 128'
print("Running:", cmd)

# Use subprocess to run and capture output
proc = subprocess.Popen(
    shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
out, err = proc.communicate(timeout=120)
print("STDOUT:\n", out)
print("STDERR:\n", err)

if proc.returncode != 0:
    raise SystemExit("gpt4all exited with code " + str(proc.returncode))
