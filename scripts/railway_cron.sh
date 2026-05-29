#!/bin/bash
# Runs on Railway cron service
# Calls the web service to refresh data and send email
# (cron containers have no external internet — web service handles SMTP)

echo "=== DDS Nightly Report $(date) ==="

python3 - <<'PYEOF'
import sys, os, json
import urllib.request
import urllib.error

base_url = os.environ.get("DDS_URL", "").rstrip("/")
if not base_url:
    print("ERROR: DDS_URL env var not set")
    sys.exit(1)

# Step 1: Refresh data
print("Refreshing DDS data...")
try:
    req = urllib.request.Request(f"{base_url}/api/refresh", method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            print(f"ERROR: Refresh failed (HTTP {resp.status})")
            sys.exit(1)
    print("Data refreshed.")
except Exception as e:
    print(f"ERROR: Refresh failed: {e}")
    sys.exit(1)

# Step 2: Send email via web service (web service has external internet for SMTP)
print("Sending nightly email...")
try:
    payload = json.dumps({"recipients": []}).encode()
    req = urllib.request.Request(f"{base_url}/api/send-email", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode()
        print(f"Done: {body}")
except urllib.error.HTTPError as e:
    print(f"ERROR: Email failed (HTTP {e.code}): {e.read().decode()}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Email failed: {e}")
    sys.exit(1)
PYEOF
