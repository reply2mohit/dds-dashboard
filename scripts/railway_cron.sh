#!/bin/bash
# Runs on Railway cron service — refreshes DDS data and emails nightly report

echo "=== DDS Nightly Report $(date) ==="

BASE_URL="${DDS_URL}"

if [[ -z "$BASE_URL" ]]; then
  echo "ERROR: DDS_URL env var not set"
  exit 1
fi

python3 - <<PYEOF
import sys, os
import urllib.request
import urllib.error
import json

base_url = os.environ["DDS_URL"].rstrip("/")

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

# Step 2: Send email
print("Sending nightly email...")
try:
    payload = json.dumps({"recipients": []}).encode()
    req = urllib.request.Request(f"{base_url}/api/send-email", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=240) as resp:
        body = resp.read().decode()
        if resp.status != 200:
            print(f"ERROR: Email failed (HTTP {resp.status}): {body}")
            sys.exit(1)
        print(f"Done: {body}")
except Exception as e:
    print(f"ERROR: Email failed: {e}")
    sys.exit(1)
PYEOF
