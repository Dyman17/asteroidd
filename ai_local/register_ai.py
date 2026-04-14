import os
import socket
import sys
import urllib.parse
import urllib.request

CLOUD_BACKEND_URL = os.getenv("CLOUD_BACKEND_URL", "https://asteroidd-server.onrender.com").strip()
AI_HOST = os.getenv("AI_HOST", "").strip()
AI_PORT = os.getenv("AI_PORT", "8000").strip()
AI_PATH = os.getenv("AI_PATH", "/analyze_bytes").strip()
DEVICE_ID = os.getenv("AI_DEVICE_ID", "ai-laptop-1").strip()


def get_local_ip() -> str:
    if AI_HOST:
        return AI_HOST
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        pass
    try:
        candidate = socket.gethostbyname(socket.gethostname())
        if candidate and not candidate.startswith("127."):
            return candidate
    except Exception:
        pass
    return "127.0.0.1"

if not CLOUD_BACKEND_URL:
    print("CLOUD_BACKEND_URL is not configured")
    sys.exit(1)

if not AI_PATH.startswith("/"):
    AI_PATH = "/" + AI_PATH

local_ip = get_local_ip()
ai_url = f"http://{local_ip}:{AI_PORT}{AI_PATH}"
ping_url = CLOUD_BACKEND_URL.rstrip("/") + "/ai/ping?" + urllib.parse.urlencode(
    {"device_id": DEVICE_ID, "ai_url": ai_url}
)

print(f"Local AI host: {local_ip}")

print("Registering AI with cloud backend:")
print(ping_url)

import json

try:
    request = urllib.request.Request(ping_url, headers={"User-Agent": "ai_local_register/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        body_bytes = response.read()
        body = body_bytes.decode("utf-8", errors="replace")
    print("Cloud backend response:")
    try:
        parsed = json.loads(body)
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(body)
except Exception as exc:
    print("Failed to register AI with cloud backend:", exc)
    sys.exit(1)
