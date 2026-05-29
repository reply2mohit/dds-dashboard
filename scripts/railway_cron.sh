#!/bin/bash
# Runs on Railway cron service — refreshes DDS data and emails nightly report

echo "=== DDS Nightly Report $(date) ==="

BASE_URL="${DDS_URL}"

if [[ -z "$BASE_URL" ]]; then
  echo "ERROR: DDS_URL env var not set"
  exit 1
fi

echo "Refreshing DDS data..."
REFRESH=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/refresh")

if [[ "$REFRESH" != "200" ]]; then
  echo "ERROR: Refresh failed (HTTP $REFRESH)"
  exit 1
fi
echo "Data refreshed."

echo "Sending nightly email..."
EMAIL=$(curl -s -o /tmp/email_resp.json -w "%{http_code}" --max-time 240 \
  -X POST "$BASE_URL/api/send-email" \
  -H "Content-Type: application/json" \
  -d '{"recipients": []}')

if [[ "$EMAIL" != "200" ]]; then
  echo "ERROR: Email failed (HTTP $EMAIL)"
  cat /tmp/email_resp.json
  exit 1
fi

echo "Done: $(cat /tmp/email_resp.json)"
