"""Example showing how to call Gemini (Generative Language API) using an API key.

This example uses `httpx` (already in `requirements.txt`) and will only perform a network
request if `GOOGLE_API_KEY` is set in the environment. Otherwise it prints instructions for
using service account based auth.
"""

import os
import json
import httpx


def call_gemini_with_api_key(prompt: str, api_key: str, model: str) -> None:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta2/{model}:generate"
    headers = {"Content-Type": "application/json"}
    payload = {"prompt": {"text": prompt}, "temperature": 0.2}
    params = {"key": api_key}

    with httpx.Client(timeout=30.0) as client:
        r = client.post(endpoint, headers=headers, json=payload, params=params)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))


def call_gemini_with_adc(prompt: str, model: str, credentials_path: str) -> None:
    # Use google-auth to create a signed JWT access token and call the REST endpoint with Bearer token
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except Exception as e:
        print("Missing google-auth libraries:", e)
        return

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=scopes
    )
    creds.refresh(Request())
    token = creds.token

    endpoint = f"https://generativelanguage.googleapis.com/v1beta2/{model}:generate"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"prompt": {"text": prompt}, "temperature": 0.2}

    with httpx.Client(timeout=30.0) as client:
        try:
            r = client.post(endpoint, headers=headers, json=payload)
            r.raise_for_status()
            print(json.dumps(r.json(), indent=2))
        except httpx.HTTPStatusError as e:
            # print status and response body for debugging (safe to share)
            resp = e.response
            print(f"HTTP error {resp.status_code}")
            try:
                print(json.dumps(resp.json(), indent=2))
            except Exception:
                print(resp.text)
        except Exception as e:
            print("Request failed:", e)


def main():
    print("Gemini Example — Smart Buddy")
    prompt = "Write a friendly 1-sentence greeting for a user starting a study plan."
    model = os.getenv("SMART_BUDDY_MODEL", "models/text-bison-001")

    api_key = os.getenv("GOOGLE_API_KEY")
    adc = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if api_key:
        print("Using API key flow")
        call_gemini_with_api_key(prompt, api_key, model)
        return

    if adc and os.path.exists(adc):
        print("Using Application Default Credentials (service account)")
        call_gemini_with_adc(prompt, model, adc)
        return

    print("No credentials found. To call Gemini:")
    print("- Set environment variable GOOGLE_API_KEY with your API key (dev only)")
    print("OR")
    print(
        "- Create a Google Service Account, download JSON, and set GOOGLE_APPLICATION_CREDENTIALS=/path/to/file.json"
    )
    print("See docs/credentials.md for step-by-step instructions (no keys in repo).")


if __name__ == "__main__":
    main()
