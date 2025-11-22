# Google Cloud SDK & Generative API (Gemini / PaLM) Setup (Optional)

This guide describes how to integrate with Google Cloud's Generative Language API (Gemini / PaLM). If you prefer to keep the project fully local and free to run, you can skip all Google Cloud steps — the repository includes a local LLM path (gpt4all) and a lightweight Transformers fallback that require no cloud billing or API keys.

Important security reminder
- Do NOT commit API keys or service account JSON files to source control. Add `*.json` and `.env` to `.gitignore`.

Overview (cloud steps are optional)
- Install Google Cloud SDK (gcloud) — only if you plan to use the cloud Generative API
- Optional: Install Visual Studio Build Tools if you plan to compile native Python extensions (not required for this repo as it uses `httpx`)
- Enable the Generative Language API and related APIs in your Google Cloud project (only if using cloud)
- Create a Service Account, grant least-privilege roles, and download JSON credentials
- Or create an API key for quick dev/testing (less secure)
- Test calls using `examples/gemini_example.py` or the Python client (cloud)

If you want a free, offline demo: use `scripts/install_gpt4all.ps1` and `examples/gpt4all_example.py` (no API keys or billing required).

1) Install Google Cloud SDK (gcloud)

- Option A — Using the helper script (PowerShell)

  The repository includes `scripts/install_google_sdks.ps1` which downloads the Cloud SDK installer and offers helper guidance. Running installers on Windows may require Administrator privileges.

  To run the helper script from PowerShell (recommended to run as Administrator):

  ```powershell
  # Open PowerShell "Run as Administrator" then:
  .\scripts\install_google_sdks.ps1
  ```

- Option B — Manual download

  1. Visit https://cloud.google.com/sdk/docs/install and follow the Windows installer instructions.
  2. After install, open a new PowerShell and confirm:

  ```powershell
  gcloud --version
  ```

2) Initialize gcloud and authenticate

```powershell
# Start interactive init; choose or create a Google Cloud project
gcloud init

# Authenticate (will open a browser)
gcloud auth login
```

3) Enable the Generative API (Generative Language) for your project

Replace `PROJECT_ID` with your project id.

```powershell
gcloud config set project PROJECT_ID
gcloud services enable generativelanguage.googleapis.com
```

You may also enable other APIs you need (e.g., Cloud Storage):

```powershell
gcloud services enable storage.googleapis.com
```

4) Create a Service Account (recommended)

```powershell
# Create a service account (replace PROJECT_ID)
gcloud iam service-accounts create smart-buddy-sa --description="Smart Buddy service account" --display-name="smart-buddy-sa"

# Grant least-privilege roles (adjust as needed). Example: roles/viewer + specific API roles.
gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:smart-buddy-sa@PROJECT_ID.iam.gserviceaccount.com" --role="roles/viewer"

# Generate a JSON key (download to a secure location)
gcloud iam service-accounts keys create "C:\path\to\smart-buddy-sa-key.json" --iam-account=smart-buddy-sa@PROJECT_ID.iam.gserviceaccount.com

# Set environment variable for local dev (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\smart-buddy-sa-key.json"
```

Notes:
- Replace `PROJECT_ID` and paths with your actual values.
- Restrict permissions on the downloaded JSON file and do not commit it.

5) (Alternative) Create an API key (quick dev only)

1. In the Google Cloud Console, go to APIs & Services > Credentials > Create Credentials > API key.
2. Restrict the key to the Generative API and/or to your IPs, then copy it to a secure place.
3. Set the environment variable for development (PowerShell):

```powershell
$env:GOOGLE_API_KEY = "YOUR_API_KEY"
```

6) Install the Python client (optional)

There is an official Python package `google-generativeai` (or you can call the REST API directly). To install:

```powershell
# Activate your virtualenv then:
pip install google-generativeai
```

Example using the `google-generativeai` client (after setting `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS`):

```python
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))  # or the client will use ADC with service account
resp = genai.generate_text(model="models/text-bison-001", prompt="Hello from Smart Buddy")
print(resp)
```

7) Test using the repository example

- Use the example script that uses `httpx`:

```powershell
# Activate virtualenv in PowerShell, then run:
python .\examples\gemini_example.py
```

If you set `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS`, the example will make a real request.

8) Troubleshooting & permissions

- If the Cloud SDK installer or Chocolatey requires elevation, run PowerShell as Administrator.
- If you cannot run installers as Administrator, use the Cloud SDK manual installation options or use API keys for dev-only testing.

9) Notes about "Google ADK"

If by "Google ADK" you meant the Android ADK or a vendor-specific AI dev kit, please clarify which SDK you need and I will add specific install steps. For Gemini/PaLM generative AI integration, the steps above (Cloud SDK + Generative API) are the main items.

10) Next steps I can perform for you

- Attempt to run the `scripts/install_google_sdks.ps1` now (requires Administrator PowerShell). I will prompt and run it if you confirm.
- After gcloud is installed, I can run the `gcloud` commands to create a service account and enable the Generative API (you must confirm project id and consent to creating resources).
