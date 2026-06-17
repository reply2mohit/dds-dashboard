#!/usr/bin/env python3
"""
Send DDS email report manually from your local machine.
Run: python3 send_now.py
"""
import json, smtplib, sys, urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

RAILWAY_URL = "https://web-production-98158.up.railway.app"

def main():
    # Load local SMTP config
    try:
        with open("email_config.json") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print("ERROR: email_config.json not found. Run from the dds-dashboard directory.")
        sys.exit(1)

    smtp_user  = cfg["sender"]
    smtp_pass  = cfg["app_password"]
    recipients = list(set(cfg.get("default_recipients", [smtp_user])))

    # Fetch live data from Railway
    print(f"Fetching data from Railway...", flush=True)
    try:
        with urllib.request.urlopen(f"{RAILWAY_URL}/api/data", timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"ERROR: Could not fetch data: {e}")
        sys.exit(1)

    print(f"Got {data['total_skus']} SKUs across {len(data['brands'])} brands.", flush=True)

    # Strip per-SKU arrays (not needed for email)
    for brand in data.get("brands", []):
        brand.pop("skus", None)

    # Build HTML
    from email_sender import build_html_body
    print("Building email HTML...", flush=True)
    html = build_html_body(data)

    subject = f"DDS Tracker — {datetime.now().strftime('%d %b %Y')}"
    msg = MIMEMultipart("alternative")
    msg["From"]    = smtp_user
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    # Send via local Gmail SMTP (works from Mac — Railway blocks this, not your Mac)
    print(f"Sending to: {', '.join(recipients)}", flush=True)
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_pass)
        smtp.sendmail(smtp_user, recipients, msg.as_string())

    print("Done! Email sent successfully.")

    # Save current state as the last-sent baseline so the dashboard shows
    # changes since this report, not since start of day
    try:
        req = urllib.request.Request(f"{RAILWAY_URL}/api/mark-sent", method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
        print(f"Baseline saved — dashboard will now show changes since {result.get('sent_at','now')}.")
    except Exception as e:
        print(f"Warning: could not save baseline ({e}). Dashboard changes counter may not reset.")

if __name__ == "__main__":
    main()
