# DDS Activity Dashboard — Handover Document

## What This Is

A local web dashboard that tracks DDS (Digital Distribution Status) progress across brands and marketplaces. It reads live data from a shared Google Sheet, displays brand-level completion stats, and sends a formatted HTML email report to stakeholders.

---

## How It Works

```
Google Sheet (team updates this)
        ↓
  data_fetcher.py (fetches as CSV every time you hit Refresh)
        ↓
  cache.json (local snapshot)
        ↓
  app.py (Flask web server → browser dashboard)
        ↓
  send_now.py (sends email report via Gmail)
```

---

## The Google Sheet

The dashboard reads from this Google Sheet:

**URL:** `https://docs.google.com/spreadsheets/d/1gQKYzhkb7j6iXqmLrDZTeXxR_2RZ5O8TaydpibK9iug`  
**Tab name:** `Sheet to be used`

The sheet must remain accessible (publicly shared or shared with the Google account running the app). The dashboard does **not** write to the sheet — it only reads.

---

## Running Locally (One-Time Setup)

### 1. Install Python

Make sure Python 3.9 or higher is installed:
```bash
python3 --version
```
Download from https://www.python.org if needed.

### 2. Install Dependencies

Open Terminal, navigate to the project folder and run:
```bash
cd /path/to/dds-dashboard
pip3 install -r requirements.txt
```

### 3. Set Up Email Config

Copy the example config and fill in your details:
```bash
cp email_config.example.json email_config.json
```

Edit `email_config.json`:
```json
{
    "sender": "your-gmail@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx",
    "default_recipients": [
        "recipient1@ergode.com",
        "recipient2@ergode.com"
    ]
}
```

**How to get a Gmail App Password:**
1. Go to your Google Account → Security
2. Enable 2-Step Verification (required)
3. Go to Security → App Passwords
4. Create a new app password (name it "DDS Dashboard")
5. Copy the 16-character password into `app_password` above

> `email_config.json` is intentionally excluded from GitHub (it contains credentials). Never commit it.

---

## Daily Usage

### Start the Dashboard

```bash
python3 app.py
```

Then open your browser at: **http://localhost:8082**

Keep the terminal window open while using the dashboard. Press `Ctrl+C` to stop it.

### Refresh Data

Click the **Refresh** button in the dashboard to pull the latest data from the Google Sheet.

### Send Email Report

With the dashboard running, either:
- Click **Send Email** in the dashboard, OR
- Run from Terminal:
  ```bash
  python3 send_now.py
  ```

The email goes to whoever is listed in `default_recipients` in your `email_config.json`.

### Change Email Recipients

Edit the `default_recipients` list in `email_config.json`. No restart needed — it reads the file fresh each time you send.

---

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Flask web server — the dashboard backend |
| `data_fetcher.py` | Fetches Google Sheet data, computes changes |
| `email_sender.py` | Builds the HTML email body |
| `send_now.py` | Sends the email report via Gmail SMTP |
| `pdf_generator.py` | Generates the management summary PDF |
| `email_config.json` | Your Gmail credentials (not in GitHub) |
| `email_config.example.json` | Template showing the required format |
| `cache.json` | Latest data snapshot (auto-generated) |
| `requirements.txt` | Python dependencies |

---

## Troubleshooting

**Dashboard shows stale data**  
Click Refresh in the browser. Data is cached locally and only updates on demand.

**"email_config.json not found"**  
You need to create it. Copy `email_config.example.json` to `email_config.json` and fill in your Gmail details.

**Email fails with authentication error**  
Your Gmail App Password is wrong or expired. Generate a new one (see setup steps above). Make sure 2-Step Verification is enabled on the Gmail account.

**Port already in use**  
Something else is running on port 8082. Either stop that process or change the port in the last line of `app.py`:
```python
app.run(host="0.0.0.0", port=8082, debug=False)
```

**Google Sheet data not loading**  
Make sure the sheet is publicly accessible: In Google Sheets → Share → Change to "Anyone with the link can view".

---

## Live Deployment (Railway)

There is also a live version running on Railway at:  
`https://web-production-98158.up.railway.app`

This is a cloud-hosted copy of the same app. The Railway deployment uses Resend (not Gmail) for sending emails since Railway blocks SMTP. Access to the Railway project may need to be transferred — contact the previous owner for Railway account access.

---

## GitHub Repository

`https://github.com/reply2mohit/dds-dashboard`

Note: `email_config.json`, `cache*.json`, and log files are excluded from GitHub via `.gitignore`. You will always need to create your own `email_config.json` after cloning.
