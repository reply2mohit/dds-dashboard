#!/bin/bash
# Runs on Railway cron service — refreshes DDS data and emails nightly report
# Email is sent directly from the cron container (not via the web service)
# so the web service worker is never stressed by heavy SMTP + PDF work.

echo "=== DDS Nightly Report $(date) ==="

python3 - <<'PYEOF'
import sys, os, json
import urllib.request
import urllib.error
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

base_url = os.environ.get("DDS_URL", "").rstrip("/")
if not base_url:
    print("ERROR: DDS_URL env var not set")
    sys.exit(1)

# ── Step 1: Refresh data on web service ──────────────────────────────────────
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

# ── Step 2: Fetch current data JSON ──────────────────────────────────────────
print("Fetching data snapshot...")
try:
    with urllib.request.urlopen(f"{base_url}/api/data", timeout=30) as resp:
        data = json.loads(resp.read())
    print(f"Got {data.get('total_skus', 0)} SKUs.")
except Exception as e:
    print(f"ERROR: Could not fetch data: {e}")
    sys.exit(1)

# ── Step 3: Build HTML email (no PDF, no matplotlib) ─────────────────────────
sys.path.insert(0, "/app")
from email_sender import build_html_body, load_config, ALWAYS_INCLUDE

print("Building email...")
config       = load_config()
sender       = config["sender"]
app_password = config["app_password"]
recipients   = config.get("default_recipients", [])
all_recip    = list(set(recipients) | {ALWAYS_INCLUDE})

html_body = build_html_body(data)

now = datetime.now().strftime("%d %b %Y")
msg = MIMEMultipart("alternative")
msg["From"]    = sender
msg["To"]      = ", ".join(all_recip)
msg["Subject"] = f"DDS Tracker — {now}"
msg.attach(MIMEText(html_body, "html"))

# ── Step 4: Send via SMTP ────────────────────────────────────────────────────
print(f"Sending to {all_recip}...")
sent = False
for port, use_ssl in [(465, True), (587, False)]:
    try:
        if use_ssl:
            with smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=30) as smtp:
                smtp.login(sender, app_password)
                smtp.sendmail(sender, all_recip, msg.as_string())
        else:
            with smtplib.SMTP("smtp.gmail.com", port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(sender, app_password)
                smtp.sendmail(sender, all_recip, msg.as_string())
        print(f"✅ Email sent via port {port} to {all_recip}")
        sent = True
        break
    except Exception as e:
        print(f"Port {port} failed: {e}")

if not sent:
    print("ERROR: All SMTP ports failed")
    sys.exit(1)
PYEOF
