import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env():
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(name, value)


def main():
    load_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set (not in environment and not in .env next to this script).")
        sys.exit(2)

    print("Key length:", len(api_key))
    print("First 4 characters:", api_key[:4])
    print("Last 4 characters:", api_key[-4:])
    print(
        "Whitespace inside key:",
        any(ch.isspace() for ch in api_key),
        "| quotes inside key:",
        any(ch in ('"', "'") for ch in api_key),
    )

    if api_key.startswith("AQ."):
        print()
        print("WARNING: this key starts with 'AQ.' That looks like a Google OAuth token,")
        print("not an AI Studio API key. AI Studio keys usually look like 'AIza...' (39 chars).")
        print("Create one at https://aistudio.google.com/apikey and put it in .env as:")
        print('GEMINI_API_KEY=AIza...')
        print()

    model = os.environ.get("WRITING_COMPANION_GATEWAY_MODEL", "gemini-3.8-flash")
    base_url = os.environ.get(
        "WRITING_COMPANION_GATEWAY_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai",
    ).rstrip("/")

    url = f"{base_url}/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "max_tokens": 10,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    print()
    print(f"Testing {model} at {base_url} ...")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            print("HTTP", response.status)
            print(body)
            print()
            print("SUCCESS: the key works and the model responded.")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print("HTTP", error.code)
        print(body)
        print()
        if error.code == 401:
            print("401: Google rejected the key. Most common causes:")
            print("  - The key is not an AI Studio key (see warning above if it starts with AQ.)")
            print("  - The key was truncated or padded when saved into .env")
            print("  - The key was created on a school-managed Google Workspace account (these are commonly blocked); use a personal Gmail account at aistudio.google.com instead")
        elif error.code == 404:
            print("404: key accepted but the model name was not found; try another model name in WRITING_COMPANION_GATEWAY_MODEL.")
        elif error.code == 403:
            print("403: the key is valid but the Generative Language API is not enabled or restricted for this account.")
        sys.exit(1)
    except urllib.error.URLError as error:
        print("Could not reach Google:", error.reason)
        print("Check your internet connection or any school/netnanny-style network filter.")
        sys.exit(1)


if __name__ == "__main__":
    main()
