import os
import sys
import time
import urllib.request
import urllib.error

url = os.environ.get("AI_HEALTH_URL", "http://localhost:8000/health")
max_attempts = 20
sleep_seconds = 1

for attempt in range(1, max_attempts + 1):
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status == 200:
                print("Local AI server is responding.")
                sys.exit(0)
    except Exception:
        if attempt == max_attempts:
            print(
                f"ERROR: Local AI server did not respond after {max_attempts} attempts.",
                file=sys.stderr,
            )
            sys.exit(1)
        time.sleep(sleep_seconds)
