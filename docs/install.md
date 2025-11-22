# Installing gpt4all and running Smart Buddy (local-first)

This guide explains how to install a local `gpt4all` binary and a test model using the included PowerShell helper, how to run the demo locally, and how to run inside Docker with your local models mounted.

## Installer: `scripts/install_gpt4all.ps1`

`scripts/install_gpt4all.ps1` is an idempotent installer that attempts to discover a suitable `gpt4all` release, download a Windows binary and a small quantized model, and verify checksums when available.

Important flags

- `-MaxRetries <n>`: retry transient downloads up to `n` times (default: 3).
- `-RetryDelay <s>`: base retry delay in seconds for exponential backoff (default: 5).
- `-VerboseOutput`: print progress and debug messages during downloads.
- `-ForceRun`: after download, attempt to execute the downloaded binary (useful for verification).
- `-SkipDownload`: skip network steps (useful for CI or when files are already present).
 - `-SkipDownload`: skip network steps (useful for CI or when files are already present).
 - `-UseBitsTransfer`: (optional) use PowerShell `Start-BitsTransfer` for downloads (shows progress and supports resuming). When not available the installer falls back to the retrying web request path.

Examples (PowerShell)

- Dry run (no network downloads):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_gpt4all.ps1 -SkipDownload -VerboseOutput
```

- Install with retries and verbose output:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_gpt4all.ps1 -MaxRetries 4 -RetryDelay 5 -VerboseOutput
```

- Install and attempt to run the binary for quick verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_gpt4all.ps1 -ForceRun
```

Checksum behavior

- When a companion checksum asset (e.g., `.sha256`) is present, the installer will download it and attempt a SHA256 verification.
- If no checksum is available, the script emits a warning and continues. Manually verify files if you require strict provenance.

Where files are placed

- Default output directory: `models/gpt4all/` under the repo root.
- The script will create the directory if missing.
- Alternatively, place your own binary and model under `models/gpt4all/` (binary `*.exe`, model `*.bin` or `*.gguf`).

## Running the demo locally

After placing a model locally (or skipping local models), run the demo:

```powershell
python examples/run_demo.py
```

Behavior notes

- If a local `gpt4all` binary and model are available under `models/gpt4all/`, the demo will use them.
- Otherwise the code will attempt Transformers as a fallback, or return a small stub response for offline testing.

## Docker usage

When running in Docker, mount your host `models/` directory into the container so the local `gpt4all` binary and models are visible inside the container.

Example (Linux/macOS):

```bash
chmod +x examples/docker_run.sh
./examples/docker_run.sh
```

Windows PowerShell: run `examples/run_in_docker.ps1` which mounts `${PWD}\models` into `/app/models` inside the container.

## Troubleshooting

- PowerShell ExecutionPolicy errors: run PowerShell as Administrator or use `-ExecutionPolicy Bypass` when invoking the script.
- If downloads fail due to transient network issues, increase `-MaxRetries` / `-RetryDelay` and retry.
- If a downloaded binary fails on Windows, ensure common Visual C++ redistributables are installed or use the Transformers fallback.

Reviewer notes and options

- The repository is reviewer-friendly and can run without cloud credentials if a local model is present. If you want, I can prepackage a tiny test model (for example `ggml-small.bin`) and add it to a release artifact or include a short fetch script.
- If you'd like a progress-bar-enabled download path, I can add an optional `Start-BitsTransfer` branch to the installer for Windows.
If you want me to add a prepackaged test model or attach a model to release artifacts, tell me which model (and confirm licensing) and I'll add it. The installer now supports `-UseBitsTransfer` to use `Start-BitsTransfer` on Windows when available.