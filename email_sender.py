"""
Sends the management PDF via Gmail SMTP.
- PDF attached
- Full HTML summary embedded in email body
- Always CC's mohit.s@ergode.com
"""
import json
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

CONFIG_FILE = "email_config.json"
ALWAYS_INCLUDE = "mohit.s@ergode.com"


def load_config():
    # Prefer env vars (Railway) over config file (local dev)
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    if smtp_user and smtp_pass:
        recipients_raw = os.environ.get("DEFAULT_RECIPIENTS", smtp_user)
        return {
            "sender": smtp_user,
            "app_password": smtp_pass,
            "default_recipients": [r.strip() for r in recipients_raw.split(",") if r.strip()],
        }
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"{CONFIG_FILE} not found. Create it with sender, app_password, and default_recipients."
        )
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_data():
    from data_fetcher import CACHE_FILE
    with open(CACHE_FILE) as f:
        import json as _j
        data = _j.load(f)
    # Drop per-SKU arrays — email only needs brand-level totals
    for brand in data.get("brands", []):
        brand.pop("skus", None)
    return data


def pct_color(pct):
    if pct >= 70:   return "#22c55e"
    elif pct >= 30: return "#f59e0b"
    else:           return "#ef4444"


def build_html_body(data):
    now       = datetime.now().strftime("%d %b %Y, %H:%M")
    total     = data["total_skus"]
    done      = data["total_completed"]
    pending   = data["total_pending"]
    ns        = data["total_not_started"]
    pct_done  = round((done / total) * 100, 1) if total else 0
    all_mp    = data["all_marketplaces"]
    az_total  = data["mp_totals"].get("Amazon", 1)

    # Exact palette from pdf_generator.py
    C_NAVY  = "#1e3a5f"
    C_INK   = "#0f172a"
    C_MUTED = "#64748b"
    C_LITE  = "#94a3b8"
    C_BORD  = "#e2e8f0"
    C_SURF  = "#f8fafc"
    C_GREEN = "#16a34a";  C_GLIT = "#dcfce7"
    C_AMBER = "#d97706";  C_ALIT = "#fef9c3"
    C_BLUE  = "#2563eb";  C_BLIT = "#dbeafe"
    C_RED   = "#dc2626";  C_RLIT = "#fee2e2"

    ch       = data.get("changes") or {}
    ch_total = ch.get("total_mp_gained", 0) + ch.get("total_dds_completed", 0)
    since    = ch.get("since", "today")

    # ── KPI tiles (exact PDF tile colors) ────────────────────────────────────
    def kpi_tile(label, value, color, bg, sub):
        return (f'<td style="width:25%; padding:16px 10px; text-align:center; background:{bg}; border:1px solid {C_BORD};">'
                f'<div style="font-size:9px; color:{C_MUTED}; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px;">{label}</div>'
                f'<div style="font-size:28px; font-weight:800; color:{color}; line-height:1.1;">{value}</div>'
                f'<div style="font-size:10px; color:{C_MUTED}; margin-top:3px;">{sub}</div>'
                f'</td>')

    kpi_html = (
        kpi_tile("TOTAL SKUs",    f"{total:,}",   C_NAVY,  C_BLIT, f"{len(data['brands'])} brands") +
        kpi_tile("COMPLETED",     f"{done:,}",    C_GREEN, C_GLIT, f"{pct_done}% of total") +
        kpi_tile("PENDING",       f"{pending:,}", C_AMBER, C_ALIT, f"{round((pending/total)*100,1) if total else 0}% of total") +
        kpi_tile("TODAY'S GAINS", f"+{ch_total}", C_BLUE,  C_BLIT, f"since {since}")
    )

    # ── Progress bar ─────────────────────────────────────────────────────────
    bar_pct  = max(int(pct_done), 1)
    rest_pct = 100 - bar_pct
    progress_html = (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="height:8px; margin:12px 0 6px;">'
        f'<tr><td style="width:{bar_pct}%; background:{C_GREEN}; height:8px;"></td>'
        f'<td style="width:{rest_pct}%; background:{C_BORD}; height:8px;"></td></tr>'
        f'</table>'
        f'<div style="font-size:11px; color:{C_GREEN}; font-weight:700; text-align:right; margin-bottom:18px;">'
        f'{pct_done}% complete &nbsp;·&nbsp; {done:,} done &nbsp;·&nbsp; {pending:,} pending</div>'
    )

    # ── Brand scorecard rows (color-coded by %, same as PDF) ─────────────────
    brand_rows = ""
    for b in data["brands"]:
        pc  = b["pct_complete"]
        col = C_GREEN if pc >= 70 else (C_AMBER if pc >= 30 else C_RED)
        bg  = C_GLIT  if pc >= 70 else (C_ALIT  if pc >= 30 else C_RLIT)
        done_w = max(pc, 1)
        rest_w = 100 - done_w
        brand_rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:7px 10px; border-bottom:1px solid {C_BORD}; color:{C_INK}; font-size:11px; font-weight:600; white-space:nowrap;">{b["name"]}</td>'
            f'<td style="padding:7px 8px; border-bottom:1px solid {C_BORD}; text-align:center; color:{C_MUTED}; font-size:11px;">{b["total"]}</td>'
            f'<td style="padding:7px 8px; border-bottom:1px solid {C_BORD}; text-align:center; color:{C_GREEN}; font-size:11px; font-weight:700;">{b["completed"]}</td>'
            f'<td style="padding:7px 8px; border-bottom:1px solid {C_BORD}; text-align:center; color:{C_AMBER}; font-size:11px; font-weight:700;">{b["pending"]}</td>'
            f'<td style="padding:7px 10px; border-bottom:1px solid {C_BORD}; min-width:90px;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" style="height:6px; margin-bottom:2px;">'
            f'<tr><td style="width:{done_w}%; background:{col}; height:6px;"></td>'
            f'<td style="width:{rest_w}%; background:{C_BORD}; height:6px;"></td></tr></table>'
            f'<div style="font-size:10px; color:{col}; font-weight:700; text-align:right;">{pc}%</div>'
            f'</td>'
            f'</tr>'
        )

    # ── Changes boxes (right column) ─────────────────────────────────────────
    def change_box(title, count, accent, by_brand, val_fmt=None):
        if not count:
            return ""
        rows = ""
        for brand, items in by_brand.items():
            if val_fmt:
                gained = list({mp for item in items for mp in item.get("gained", [])})
                val = val_fmt(gained)
            else:
                val = f"+{len(items)}"
            rows += (f'<tr>'
                     f'<td style="padding:4px 0; color:{C_INK}; font-size:11px; border-bottom:1px solid {C_BORD};">{brand}</td>'
                     f'<td style="padding:4px 0; color:{accent}; font-weight:700; font-size:11px; text-align:right; border-bottom:1px solid {C_BORD}; white-space:nowrap;">{val}</td>'
                     f'</tr>')
        return (f'<div style="background:#ffffff; border:1px solid {C_BORD}; border-left:3px solid {accent}; '
                f'border-radius:6px; padding:12px 14px; margin-bottom:10px;">'
                f'<div style="font-size:9px; color:{C_MUTED}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:4px;">{title}</div>'
                f'<div style="font-size:28px; font-weight:800; color:{accent}; line-height:1; margin-bottom:8px;">+{count}</div>'
                f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
                f'</div>')

    changes_col = ""
    if ch.get("total_dds_completed", 0) > 0:
        changes_col += change_box("DDS UPDATES", ch["total_dds_completed"], C_GREEN, ch.get("dds_completed_by_brand", {}))
    if ch.get("total_mp_gained", 0) > 0:
        changes_col += change_box("NEW MP LINKS", ch["total_mp_gained"], C_AMBER, ch.get("mp_gained_by_brand", {}),
                                  val_fmt=lambda mps: ", ".join(mps[:3]) + ("…" if len(mps) > 3 else ""))
    if ch.get("total_new_skus", 0) > 0:
        changes_col += change_box("NEW SKUs", ch["total_new_skus"], C_BLUE, ch.get("new_skus_by_brand", {}))
    if not changes_col:
        changes_col = f'<div style="font-size:12px; color:{C_LITE}; padding:12px 0;">No changes since last snapshot.</div>'

    changes_label = (f'<div style="font-size:12px; font-weight:700; color:{C_INK}; margin-bottom:8px;">'
                     f'Today\'s Changes'
                     f'<span style="font-size:10px; color:{C_MUTED}; font-weight:400; margin-left:6px;">since {since}</span>'
                     f'</div>')

    # ── Channel matrix ────────────────────────────────────────────────────────
    mp_header = f'<th style="padding:7px 10px; background:{C_NAVY}; color:#ffffff; font-size:10px; border:1px solid #2d4a6e; white-space:nowrap; text-align:left;">Brand</th>'
    for mp in all_mp:
        mp_header += f'<th style="padding:7px 5px; background:{C_NAVY}; color:#93c5fd; font-size:9px; border:1px solid #2d4a6e; text-align:center; white-space:nowrap;">{mp}</th>'

    mp_rows = ""
    for i, b in enumerate(data["brands"]):
        bg    = "#ffffff" if i % 2 == 0 else C_SURF
        cells = f'<td style="padding:7px 10px; background:{bg}; color:{C_INK}; font-size:10px; font-weight:600; border:1px solid {C_BORD}; white-space:nowrap;">{b["name"]}</td>'
        for mp in all_mp:
            cnt = b["mp_sku_counts"].get(mp, 0)
            if cnt > 0:
                cells += f'<td style="padding:7px 5px; background:{bg}; color:{C_GREEN}; font-weight:700; font-size:10px; text-align:center; border:1px solid {C_BORD};">{cnt}</td>'
            else:
                cells += f'<td style="padding:7px 5px; background:{bg}; color:{C_BORD}; font-size:10px; text-align:center; border:1px solid {C_BORD};">—</td>'
        mp_rows += f"<tr>{cells}</tr>"

    total_cells = f'<td style="padding:7px 10px; background:{C_SURF}; color:{C_MUTED}; font-size:10px; border:1px solid {C_BORD}; border-top:2px solid {C_NAVY}; font-weight:700;">TOTAL</td>'
    for mp in all_mp:
        cnt = data["mp_totals"].get(mp, 0)
        total_cells += f'<td style="padding:7px 5px; background:{C_SURF}; color:{C_INK}; font-weight:700; font-size:10px; text-align:center; border:1px solid {C_BORD}; border-top:2px solid {C_NAVY};">{cnt if cnt else "—"}</td>'
    mp_rows += f"<tr>{total_cells}</tr>"

    pct_cells = f'<td style="padding:7px 10px; background:{C_SURF}; color:{C_MUTED}; font-size:9px; border:1px solid {C_BORD};">% of Amazon</td>'
    for mp in all_mp:
        cnt = data["mp_totals"].get(mp, 0)
        if mp == "Amazon":
            pct_cells += f'<td style="padding:7px 5px; background:{C_SURF}; color:{C_BLUE}; font-weight:700; font-size:10px; text-align:center; border:1px solid {C_BORD};">100%</td>'
        elif cnt > 0:
            pv  = round((cnt / az_total) * 100, 1)
            col = C_GREEN if pv >= 50 else C_BLUE if pv >= 20 else C_AMBER if pv >= 10 else C_RED
            pct_cells += f'<td style="padding:7px 5px; background:{C_SURF}; color:{col}; font-weight:700; font-size:10px; text-align:center; border:1px solid {C_BORD};">{pv}%</td>'
        else:
            pct_cells += f'<td style="padding:7px 5px; background:{C_SURF}; color:{C_BORD}; font-size:10px; text-align:center; border:1px solid {C_BORD};">—</td>'
    mp_rows += f"<tr>{pct_cells}</tr>"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:{C_SURF}; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{C_SURF}; padding:20px 12px;">
  <tr><td>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:10px; overflow:hidden; max-width:860px; margin:0 auto; border:1px solid {C_BORD};">
      <tr><td>

        <!-- Navy header -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{C_NAVY};">
          <tr>
            <td style="padding:16px 20px;">
              <div style="font-size:18px; font-weight:700; color:#ffffff;">DDS Tracker</div>
              <div style="font-size:10px; color:#93c5fd; margin-top:2px;">Ergode International &nbsp;·&nbsp; {now}</div>
            </td>
            <td style="padding:16px 20px; text-align:right; vertical-align:middle;">
              <span style="background:rgba(255,255,255,0.15); color:#ffffff; padding:4px 12px; border-radius:20px; font-size:10px; font-weight:600; letter-spacing:0.5px;">AUTOMATED REPORT</span>
            </td>
          </tr>
        </table>

        <table width="100%" cellpadding="0" cellspacing="0" style="padding:16px 20px 20px;">
          <tr><td>

            <!-- KPI tiles -->
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; margin-bottom:0;">
              <tr>{kpi_html}</tr>
            </table>

            <!-- Progress bar + label -->
            {progress_html}

            <!-- Two-column: Brand Scorecard (left 58%) | Changes (right 42%) -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
              <tr valign="top">
                <!-- LEFT: Brand Scorecard -->
                <td style="width:58%; padding-right:12px;">
                  <div style="font-size:11px; font-weight:700; color:{C_NAVY}; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">Brand Scorecard</div>
                  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; border:1px solid {C_BORD}; border-radius:6px; overflow:hidden;">
                    <thead>
                      <tr style="background:{C_NAVY};">
                        <th style="padding:7px 10px; text-align:left; color:#ffffff; font-size:9px; font-weight:600; border:1px solid #2d4a6e;">Brand</th>
                        <th style="padding:7px 7px; text-align:center; color:#93c5fd; font-size:9px; font-weight:600; border:1px solid #2d4a6e;">Tot</th>
                        <th style="padding:7px 7px; text-align:center; color:#86efac; font-size:9px; font-weight:600; border:1px solid #2d4a6e;">Done</th>
                        <th style="padding:7px 7px; text-align:center; color:#fcd34d; font-size:9px; font-weight:600; border:1px solid #2d4a6e;">Pend</th>
                        <th style="padding:7px 10px; text-align:left; color:#93c5fd; font-size:9px; font-weight:600; border:1px solid #2d4a6e; min-width:80px;">Progress</th>
                      </tr>
                    </thead>
                    <tbody>{brand_rows}</tbody>
                  </table>
                </td>
                <!-- RIGHT: Changes boxes -->
                <td style="width:42%; padding-left:4px; vertical-align:top;">
                  <div style="font-size:11px; font-weight:700; color:{C_NAVY}; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">Today's Changes</div>
                  <div style="font-size:10px; color:{C_MUTED}; margin-bottom:10px;">since {since}</div>
                  {changes_col}
                </td>
              </tr>
            </table>

            <!-- Channel Distribution -->
            <div style="font-size:11px; font-weight:700; color:{C_NAVY}; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">Channel Distribution</div>
            <div style="font-size:10px; color:{C_MUTED}; margin-bottom:8px;">SKUs live per marketplace · last row = % vs Amazon</div>
            <div style="overflow-x:auto;">
              <table cellpadding="0" cellspacing="0" style="border-collapse:collapse; min-width:600px; width:100%; border:1px solid {C_BORD};">
                <thead><tr>{mp_header}</tr></thead>
                <tbody>{mp_rows}</tbody>
              </table>
            </div>

            <!-- Footer -->
            <div style="margin-top:20px; padding-top:12px; border-top:1px solid {C_BORD}; font-size:10px; color:{C_LITE}; text-align:center;">
              DDS Tracker &nbsp;·&nbsp; {now}
            </div>

          </td></tr>
        </table>

      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    return html


def send_pdf(pdf_path, recipients, subject=None):
    config       = load_config()
    sender       = config["sender"]
    app_password = config["app_password"]

    # Always include mohit
    all_recipients = list({r.strip() for r in (recipients if isinstance(recipients, list) else [recipients])} | {ALWAYS_INCLUDE})

    if not subject:
        subject = f"DDS Tracker — {datetime.now().strftime('%d %b %Y')}"

    data     = load_data()
    html_body = build_html_body(data)

    msg = MIMEMultipart("mixed")
    msg["From"]    = sender
    msg["To"]      = ", ".join(all_recipients)
    msg["Subject"] = subject

    # HTML body
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    # PDF attachment
    with open(pdf_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename="DDS_Management_Summary.pdf")
        msg.attach(attachment)

    # JSON data backup attachment
    from data_fetcher import CACHE_FILE
    try:
        with open(CACHE_FILE, "rb") as f:
            json_attach = MIMEApplication(f.read(), _subtype="json")
            date_str = datetime.now().strftime("%Y-%m-%d")
            json_attach.add_header("Content-Disposition", "attachment", filename=f"dds_data_{date_str}.json")
            msg.attach(json_attach)
    except FileNotFoundError:
        pass

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(sender, app_password)
        smtp.sendmail(sender, all_recipients, msg.as_string())

    return all_recipients


def _send_via_resend(api_key, from_addr, recipients, subject, html_body):
    """Send email via Resend HTTP API (works on Railway — uses HTTPS port 443)."""
    import urllib.request as _req
    import json as _json
    payload = _json.dumps({
        "from": from_addr,
        "to": recipients,
        "subject": subject,
        "html": html_body,
    }).encode()
    request = _req.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with _req.urlopen(request, timeout=30) as resp:
        return _json.loads(resp.read())


def send_html_only(recipients, subject=None):
    """Send HTML email via Resend API. Uses pre-cached HTML from /api/refresh if available."""
    print("[email] Loading config...", flush=True)
    config = load_config()

    all_recipients = list(
        {r.strip() for r in (recipients if isinstance(recipients, list) else [recipients])}
        | {ALWAYS_INCLUDE}
    )

    if not subject:
        subject = f"DDS Tracker — {datetime.now().strftime('%d %b %Y')}"

    # Use pre-cached HTML (generated during refresh) to avoid loading all data into memory
    from data_fetcher import DATA_DIR
    email_html_path = str(DATA_DIR / "email_cache.html")
    if os.path.exists(email_html_path):
        print("[email] Using cached HTML.", flush=True)
        with open(email_html_path) as f:
            html_body = f.read()
    else:
        print("[email] No cache — building HTML from data.", flush=True)
        data = load_data()
        html_body = build_html_body(data)

    print(f"[email] HTML ready ({len(html_body)} bytes). Sending via Resend...", flush=True)

    resend_key = os.environ.get("RESEND_API_KEY", "")
    from_addr  = os.environ.get("FROM_EMAIL", f"DDS Tracker <{config.get('sender', ALWAYS_INCLUDE)}>")

    if not resend_key:
        raise RuntimeError("RESEND_API_KEY env var not set — add it in Railway Variables")

    result = _send_via_resend(resend_key, from_addr, all_recipients, subject, html_body)
    print(f"[email] Sent. Resend ID: {result.get('id')}", flush=True)
    return all_recipients


if __name__ == "__main__":
    import sys
    recipients = sys.argv[1:] if len(sys.argv) > 1 else load_config().get("default_recipients", [])
    from pdf_generator import build_pdf
    pdf = build_pdf()
    sent_to = send_pdf(pdf, recipients)
    print(f"Email sent to: {sent_to}")
