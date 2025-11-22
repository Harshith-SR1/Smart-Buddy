# Credentials & Gemini (Generative API) Integration (Optional)

If you prefer to keep the project fully local and free to run, you can skip the cloud steps in this document. The repository includes a local LLM fallback (gpt4all) and a small Transformers example that do not require any Google credentials or billing. Use those for offline demos and testing.

This document explains how to provide credentials for the Google Generative API (Gemini/PaLM) **safely**.

Important: Do NOT commit API keys or service account JSON files to source control. Add secrets to `.gitignore`.

Development options

- API Key (quick, less secure — use only for dev/test)
  1. Create an API key in the Google Cloud Console for the project with the Generative API enabled.
  2. Set `GOOGLE_API_KEY` in your shell or in a local `.env` file (not committed):

```powershell
$env:GOOGLE_API_KEY = "YOUR_API_KEY"
```

- Service Account (recommended for production)
  1. In Google Cloud Console, create or choose a project.
  2. Enable the "Generative Language API" (or appropriate product).
  3. Create a Service Account and grant least-privilege roles required by the API.
  4. Create and download a JSON key for the Service Account.
  5. Set the environment variable:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\service-account.json"
```

Notes and best practices

- Never commit `service-account.json` or API keys. Add `*.json` and `.env` to `.gitignore`.
- For CI, store secrets in the CI provider's secret store and inject at runtime.
- Rotate keys regularly and scope permissions to least privilege.
- For local development, prefer `GOOGLE_APPLICATION_CREDENTIALS` with a low-privileged service account.

Using the example

- `examples/gemini_example.py` demonstrates how to call Gemini with `GOOGLE_API_KEY` using `httpx`.
- If you want a client library that uses `GOOGLE_APPLICATION_CREDENTIALS` automatically, use `google-auth` + the official client libraries (the repo already contains required packages).
