"""Send checkpointable JSON requests without exposing local credentials.

Requests use provider defaults. Follow-up studies supply an explicit conversation.
Raw request/response bodies are retained by the study runner, without headers.
"""

import json
import os
import shlex
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from src.study_io import ROOT

TIMEOUT_SECONDS = 90
MAX_ATTEMPTS = 2


def load_key() -> str:
    """Read the configured key into memory without printing or persisting it."""
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    for path in (ROOT / ".env", ROOT.parent / ".env"):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip().startswith("OPENAI_API_KEY="):
                return shlex.split(line.split("=", 1)[1].strip())[0]
    raise ValueError("Set OPENAI_API_KEY in your shell or local .env.")


def query(prompt: str, model: str, key: str) -> dict:
    """Request one JSON answer, retaining raw output and provider metadata."""
    return query_messages([{"role": "user", "content": prompt}], model, key)


def query_messages(messages: list, model: str, key: str) -> dict:
    """Send an explicit conversation and retain the exact request and raw answer."""
    body = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(MAX_ATTEMPTS):
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw = json.loads(response.read())
            content = raw["choices"][0]["message"]["content"]
            return {
                "request": body,
                "raw_response": raw,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "answer_text": content,
            }
        except urllib.error.HTTPError as error:
            retry = error.code in (408, 429) or error.code >= 500
            if not retry or attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError(
                    f"OpenAI HTTP {error.code}; response not recorded."
                ) from None
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            if attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError(
                    "Network request failed after two attempts; resume missing keys."
                ) from None
        time.sleep(2**attempt)
    raise RuntimeError("No response received.")
