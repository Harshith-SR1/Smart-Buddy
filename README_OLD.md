# Smart Buddy — Multi-agent prototype

Smart Buddy is a local-first, multi-agent prototype demonstrating a Router, Intent/Task/Planner/Emotion agents, a small SQLite-backed MemoryBank, and an LLM wrapper with cloud and local fallbacks.

This repository is intended to run without requiring cloud billing: by default the LLM wrapper will try cloud ADC/API-key flows, then fall back to local `gpt4all` or a Transformers stub.

## Quickstart (Windows PowerShell)

1) Create and activate a virtual environment

```powershell
# Smart Buddy — Multi-agent prototype

Smart Buddy is a local-first, multi-agent prototype demonstrating a Router, Intent/Task/Planner/Emotion agents, a small SQLite-backed MemoryBank, and an LLM wrapper with cloud and local fallbacks.

This repository is intended to run without requiring cloud billing: by default the LLM wrapper will try cloud ADC/API-key flows, then fall back to local `gpt4all` or a Transformers stub.

## Quickstart (Windows PowerShell)

Follow these steps to run the demo locally on Windows. The project is local-first — no cloud billing required.

1) Create and activate a virtual environment

```powershell
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
```

2) Install runtime dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

3) (Optional for development/tests) install editable package with dev extras

```powershell
pip install -e .[dev]
```

4) (Optional) Install gpt4all local binary + model

Use the provided installer to download a Windows binary and a small quantized model. The script is idempotent and supports retries and checksum verification when available:

```powershell
# from repo root
powershell -ExecutionPolicy Bypass -File .\scripts\install_gpt4all.ps1 -MaxRetries 4 -RetryDelay 5 -VerboseOutput
```

Manual placement: put the binary and model files under `models/gpt4all/` (binary `*.exe`, model `*.bin` or `*.gguf`).

5) Run the demo

```powershell
python examples/run_demo.py
```

## Docker (optional)

Build and run using the helper script. Make sure to mount your `models` directory so local LLMs are available inside the container.

Linux/macOS:

```bash
chmod +x examples/docker_run.sh
./examples/docker_run.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\examples\run_in_docker.ps1
```

## Environment variables

- `GOOGLE_API_KEY` — optional API key for cloud Generative API.
- `GOOGLE_APPLICATION_CREDENTIALS` — optional path to a service account JSON for ADC.
- `SMART_BUDDY_MODEL` — optional override for cloud model name.

## Notes & troubleshooting

- Checksum verification: the installer will attempt to download companion checksum assets (e.g., `.sha256`) and verify SHA256 when available. When a checksum is not available the installer will warn and continue — manual verification is recommended for security-conscious installs.
- Docker mounts: the example Docker scripts mount your host `models/` into the container. Ensure your models are in `models/gpt4all/` before running the container.
- Tests: run the full test suite with `pytest` (we use `pytest==7.x` in CI).

Common issues

- PowerShell ExecutionPolicy errors: use `-ExecutionPolicy Bypass` or run PowerShell as Administrator for the install script.
- Missing VC runtimes on Windows: if a downloaded `gpt4all` binary fails to run, ensure common Visual C++ redistributables are installed or use the included Transformers fallback.
- Network failures: retry with increased `-MaxRetries` / `-RetryDelay` on the installer.

Reviewer note

- The repo is designed to run offline once a local model is present. If you'd like, I can prepackage a small test model and include it in the repo or provide a short script to fetch a lightweight model for reviewers. Tell me which `gpt4all` model you'd like prepackaged and I will add a note in `docs/install.md` and optionally add it to the release artifacts.

## Files of interest

- `smart_buddy/` — core package (agents, llm, memory, prompting, safety, logging)
- `scripts/install_gpt4all.ps1` — idempotent installer with retry/backoff and checksum fallback
- `examples/run_demo.py` — small interactive demo runner
- `tests/` — unit and integration tests (use `pytest`)
