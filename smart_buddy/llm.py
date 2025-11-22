"""Minimal LLM wrapper with ADC-first behavior and safe fallbacks.

Features:
- Prefer Application Default Credentials (ADC) when available (service account JSON or default ADC).
- Fall back to API key path if ADC not available.
- Return structured error dicts on HTTP/request failures instead of raising.
- Simple retry with exponential backoff for transient errors.
"""

import os
import time
import random
from typing import Any, Dict, Optional
from .logging import get_logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import requests
from requests import RequestException
import subprocess
import shlex
from pathlib import Path
import google.generativeai as genai  # type: ignore
from . import safety


class LLM:
    def __init__(self):
        self._logger = get_logger(__name__)
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model = os.getenv("SMART_BUDDY_MODEL", "gemini-2.5-flash")
        # scopes required to call Google Generative API
        self._scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        # Configure the generative AI client
        try:
            genai.configure(api_key=self.api_key)  # type: ignore
        except Exception:
            pass

    def _get_adc_token(self) -> Optional[str]:
        """Try to obtain an access token via ADC.

        Returns the bearer token string or None if ADC not available.
        """
        # import google auth libraries lazily
        try:
            from google.oauth2 import service_account
            import google.auth
            from google.auth.transport.requests import Request
        except Exception:
            return None

        # If explicit service account path provided, use it
        sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        creds = None
        try:
            if sa_path and os.path.exists(sa_path):
                creds = service_account.Credentials.from_service_account_file(
                    sa_path, scopes=self._scopes
                )
            else:
                creds, _project = google.auth.default(scopes=self._scopes)

            # refresh to obtain access token
            req = Request()
            if hasattr(creds, "refresh"):
                creds.refresh(req)  # type: ignore
            return getattr(creds, "token", None)
        except Exception:
            return None

    def _post_with_retries(
        self,
        endpoint: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        attempts = 0
        max_attempts = 4
        self._logger.debug(
            "post_with_retries_start",
            extra={"endpoint": endpoint, "payload_len": len(str(payload))},
        )
        while attempts < max_attempts:
            status = None
            try:
                r = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    params=(params or {}),
                    timeout=15,
                )
                # inspect status before raising to avoid retrying 4xx
                status = getattr(r, "status_code", None)
                if status is not None:
                    # Do not retry on client errors; return immediately
                    if 400 <= status < 500:
                        return {
                            "error": "request_exception",
                            "message": f"client error: {status}",
                            "status": status,
                        }
                    # retry on server errors
                    if 500 <= status < 600:
                        raise RequestException(f"server error: {status}")
                r.raise_for_status()
                try:
                    data = r.json()
                except Exception:
                    data = None
                if data is None:
                    return {"error": "empty_response"}
                return data
            except RequestException as e:
                attempts += 1
                self._logger.warning(
                    "post_with_retries_attempt_failed",
                    extra={"endpoint": endpoint, "attempt": attempts, "error": str(e)},
                )
                if attempts >= max_attempts:
                    self._logger.error(
                        "post_with_retries_failed",
                        extra={"endpoint": endpoint, "attempts": attempts},
                    )
                    return {
                        "error": "request_exception",
                        "message": str(e),
                        "status": status,
                    }
                backoff = 0.5 * (2 ** (attempts - 1)) + random.uniform(0, 0.1)
                time.sleep(backoff)
        # Fallback return to satisfy type checker
        return {"error": "unknown"}

    def _post_with_retries_trace(
        self,
        endpoint: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Same as `_post_with_retries` but includes `trace_id` in all logs for correlation."""
        attempts = 0
        max_attempts = 4
        self._logger.debug(
            "post_with_retries_start",
            extra={
                "endpoint": endpoint,
                "payload_len": len(str(payload)),
                "trace_id": trace_id,
            },
        )
        while attempts < max_attempts:
            status = None
            try:
                r = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    params=(params or {}),
                    timeout=15,
                )
                status = getattr(r, "status_code", None)
                if status is not None:
                    if 400 <= status < 500:
                        return {
                            "error": "request_exception",
                            "message": f"client error: {status}",
                            "status": status,
                        }
                    if 500 <= status < 600:
                        raise RequestException(f"server error: {status}")
                r.raise_for_status()
                try:
                    data = r.json()
                except Exception:
                    data = None
                if data is None:
                    return {"error": "empty_response"}
                return data
            except RequestException as e:
                attempts += 1
                self._logger.warning(
                    "post_with_retries_attempt_failed",
                    extra={
                        "endpoint": endpoint,
                        "attempt": attempts,
                        "error": str(e),
                        "trace_id": trace_id,
                    },
                )
                if attempts >= max_attempts:
                    self._logger.error(
                        "post_with_retries_failed",
                        extra={
                            "endpoint": endpoint,
                            "attempts": attempts,
                            "trace_id": trace_id,
                        },
                    )
                    return {
                        "error": "request_exception",
                        "message": str(e),
                        "status": status,
                    }
                backoff = 0.5 * (2 ** (attempts - 1)) + random.uniform(0, 0.1)
                time.sleep(backoff)
        # Fallback return to satisfy type checker
        return {"error": "unknown"}

    def generate(self, prompt: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        # Run local moderation before any generation attempt
        try:
            mod = safety.moderate_text(prompt, trace_id=trace_id)
            self._logger.debug("moderation_result", extra={"moderation": mod})
            if not mod.get("allowed", True):
                self._logger.info("generation_blocked_by_safety", extra={"reason": mod})
                return {"error": "safety_block", "moderation": mod}
        except Exception:
            # If moderation fails unexpectedly, continue but note this in response
            self._logger.exception("moderation_failed")
        # Prepare cloud endpoint + payload for Generative API
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta2/{self.model}:generate"
        )
        payload = {"prompt": {"text": prompt}, "temperature": 0.2}

        # Use the new google.generativeai SDK
        try:
            self._logger.info("using_google_genai_sdk", extra={"trace_id": trace_id})
            model = genai.GenerativeModel(self.model)  # type: ignore
            response = model.generate_content(prompt)  # type: ignore
            return {"candidates": [{"content": response.text}]}  # type: ignore
        except Exception as e:
            self._logger.warning(
                "google_genai_sdk_failed",
                extra={"error": str(e), "trace_id": trace_id},
            )
            # Fall through to older ADC method if the new SDK fails
            pass

        # 1) Try ADC (preferred) unless explicitly disabled
        token = None
        if os.getenv("SMART_BUDDY_DISABLE_ADC") != "1":
            token = self._get_adc_token()
        if token:
            self._logger.info("using_adc_for_generation", extra={"trace_id": trace_id})
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
            try:
                # Prefer calling the (possibly monkeypatched) `_post_with_retries` if present
                res = self._post_with_retries(endpoint, headers, payload)
                # annotate logs to include trace_id for correlation
                self._logger.debug(
                    "post_with_retries_used",
                    extra={"endpoint": endpoint, "trace_id": trace_id},
                )
            except TypeError:
                res = self._post_with_retries_trace(
                    endpoint, headers, payload, trace_id=trace_id
                )
            if isinstance(res, dict) and res.get("error"):
                # If the error originates from network/requests, decide based on HTTP status
                if res.get("error") == "request_exception":
                    status = res.get("status")
                    # For client-side 4xx errors (e.g. 404 model not found), continue to local fallbacks.
                    if status is not None and 400 <= status < 500:
                        self._logger.info(
                            "adc_client_error_fallback", extra={"status": status}
                        )
                    else:
                        return res
                else:
                    self._logger.warning(
                        "adc_generation_error", extra={"error": res.get("message")}
                    )
            else:
                return res

        # 2) Try API key if present
        if self.api_key:
            self._logger.info(
                "using_api_key_for_generation", extra={"trace_id": trace_id}
            )
            headers = {"Content-Type": "application/json"}
            params = {"key": self.api_key}
            try:
                res = self._post_with_retries(endpoint, headers, payload, params=params)
                self._logger.debug(
                    "post_with_retries_used",
                    extra={"endpoint": endpoint, "trace_id": trace_id},
                )
            except TypeError:
                res = self._post_with_retries_trace(
                    endpoint, headers, payload, params=params, trace_id=trace_id
                )
            if isinstance(res, dict) and res.get("error"):
                if res.get("error") == "request_exception":
                    status = res.get("status")
                    if status is not None and 400 <= status < 500:
                        self._logger.info(
                            "api_key_client_error_fallback", extra={"status": status}
                        )
                    else:
                        return res
                else:
                    self._logger.warning(
                        "api_key_generation_error", extra={"error": res.get("message")}
                    )
            else:
                return res

        # 3) Try local GPT4All Python wrapper if available (offline, free)
        try:
            # Prefer Python binding if installed and a model file is present
            repo_root = Path(__file__).resolve().parents[1]
            gpt4_dir = repo_root / "models" / "gpt4all"
            model_file = None
            if gpt4_dir.exists():
                for p in gpt4_dir.iterdir():
                    if p.is_file() and p.suffix in [".gguf", ".bin"]:
                        model_file = p
                        break
            if model_file is not None:
                from gpt4all import GPT4All  # type: ignore[import-not-found]

                self._logger.info(
                    "using_gpt4all_python",
                    extra={"model": str(model_file), "trace_id": trace_id},
                )
                llm = GPT4All(
                    model_name=model_file.name,
                    model_path=str(gpt4_dir),
                    allow_download=False,
                )
                with llm.chat_session():
                    content = llm.generate(prompt, max_tokens=256)
                return {"candidates": [{"content": content}]}
        except Exception:
            # Fall through to binary/other fallbacks
            self._logger.exception(
                "gpt4all_python_failed", extra={"trace_id": trace_id}
            )

        # 4) Try local gpt4all binary if available (offline, free)
        # Look for models/gpt4all/gpt4all.exe and any model file below models/gpt4all
        repo_root = Path(__file__).resolve().parents[1]
        gpt4_dir = repo_root / "models" / "gpt4all"
        binary = gpt4_dir / "gpt4all.exe"
        model_file = None
        if gpt4_dir.exists():
            for p in gpt4_dir.iterdir():
                if p.is_file() and (
                    p.name.startswith("ggml") or p.suffix in [".bin", ".bin.gz"]
                ):
                    model_file = p
                    break

        if binary.exists() and model_file:
            try:
                self._logger.info(
                    "using_gpt4all_local_binary",
                    extra={"binary": str(binary), "model": str(model_file)},
                )
                cmd = f'"{binary}" --model "{model_file}" --prompt "{prompt}" --n_predict 256'
                proc = subprocess.Popen(
                    shlex.split(cmd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                out, err = proc.communicate(timeout=120)
                # Prefer stdout if present
                content = out.strip() if out and out.strip() else err.strip()
                self._logger.debug(
                    "gpt4all_output",
                    extra={"out_len": len(content), "trace_id": trace_id},
                )
                return {"candidates": [{"content": content}]}
            except Exception as e:
                self._logger.exception(
                    "gpt4all_invoke_failed",
                    extra={"error": str(e), "trace_id": trace_id},
                )
                # Fall through to transformer fallback
                pass

        # 5) Local transformers fallback (distilgpt2) if installed
        try:
            from transformers import pipeline  # type: ignore[import-not-found]

            self._logger.info(
                "using_transformers_fallback",
                extra={"model": "distilgpt2", "trace_id": trace_id},
            )
            generator = pipeline("text-generation", model="distilgpt2")
            res = generator(prompt, max_length=80, num_return_sequences=1)
            return {"candidates": [{"content": res[0]["generated_text"]}]}
        except Exception:
            self._logger.exception(
                "transformers_fallback_failed", extra={"trace_id": trace_id}
            )
            # 6) Offline stub fallback
            self._logger.info("using_stub_fallback", extra={"trace_id": trace_id})
            return {"candidates": [{"content": f"[stub reply] {prompt[:200]}"}]}

        # Use the downloaded GGUF model
        model_path = Path(f"{os.getcwd()}/models/gpt4all/orca-2-7b.Q4_K_M.gguf")
        if not model_path.exists():
            self.logger.error("gpt4all_model_not_found", model_path=str(model_path))
            return None

        from gpt4all import GPT4All  # type: ignore[import-not-found]

        self._logger.info(
            "using_gpt4all_gguf",
            extra={"model": str(model_path), "trace_id": trace_id},
        )
        llm = GPT4All(
            model_name=model_path.name,
            model_path=str(model_path.parent),
            allow_download=False,
        )
        with llm.chat_session():
            content = llm.generate(prompt, max_tokens=256)
        return {"candidates": [{"content": content}]}
