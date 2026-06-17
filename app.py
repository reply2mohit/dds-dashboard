import os
from flask import Flask, render_template, jsonify, send_file, request
from data_fetcher import fetch_and_process, load_cache

app = Flask(__name__)

@app.route("/")
def index():
    data = load_cache()
    if not data:
        data = fetch_and_process()
    return render_template("index.html", data=data)

@app.route("/api/refresh", methods=["POST"])
def refresh():
    data = fetch_and_process()
    # Pre-generate email HTML while data is already in memory (avoids OOM on /api/send-email)
    try:
        from email_sender import build_html_body
        from data_fetcher import DATA_DIR
        slim_brands = [{k: v for k, v in b.items() if k != "skus"} for b in data.get("brands", [])]
        slim = dict(data, brands=slim_brands)
        html = build_html_body(slim)
        with open(str(DATA_DIR / "email_cache.html"), "w") as f:
            f.write(html)
        print("[refresh] Email HTML cached.", flush=True)
    except Exception as e:
        print(f"[refresh] Warning: could not cache email HTML: {e}", flush=True)
    return jsonify({"status": "ok", "last_updated": data["last_updated"]})

@app.route("/api/data")
def api_data():
    data = load_cache()
    if not data:
        data = fetch_and_process()
    return jsonify(data)

@app.route("/download-pdf")
def download_pdf():
    from pdf_generator import build_pdf
    from data_fetcher import DATA_DIR
    path = build_pdf(str(DATA_DIR / "management_summary.pdf"))
    return send_file(os.path.abspath(path), as_attachment=True, download_name="DDS_Summary.pdf")

@app.route("/api/force-complete", methods=["POST"])
def force_complete():
    from data_fetcher import save_forced_completions, fetch_and_process
    from datetime import datetime
    body = request.get_json()
    asins = [a.strip() for a in body.get("asins", []) if a.strip()]
    mp_updates = body.get("mp_updates", [])  # list of {asin, marketplaces:[...]}
    if not asins and not mp_updates:
        return jsonify({"status": "error", "message": "No ASINs or marketplace updates provided"}), 400
    today = datetime.now().strftime("%Y-%m-%d")
    saved = save_forced_completions(asins, today, mp_updates=mp_updates)
    data = fetch_and_process()
    return jsonify({"status": "ok", "forced_asins": saved, "last_updated": data["last_updated"]})


@app.route("/api/reset-baseline", methods=["POST"])
def reset_baseline():
    """Reset baseline to current cache — zeroes out all change counters."""
    import json
    from data_fetcher import CACHE_FILE, DAILY_BASELINE_FILE
    from datetime import datetime
    try:
        with open(CACHE_FILE) as f:
            current = json.load(f)
        current["baseline_date"] = datetime.now().strftime("%Y-%m-%d")
        with open(DAILY_BASELINE_FILE, "w") as f:
            json.dump(current, f)
        return jsonify({"status": "ok", "message": "Baseline reset to current data — changes now start from zero"})
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "No data yet — run Refresh first"}), 404


@app.route("/api/mark-sent", methods=["POST"])
def mark_sent():
    """Save current cache as the last-sent baseline so future diffs start from here."""
    from data_fetcher import save_last_sent_baseline
    from datetime import datetime
    ok = save_last_sent_baseline()
    if ok:
        return jsonify({"status": "ok", "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return jsonify({"status": "error", "message": "No cache yet — run Refresh first"}), 404


@app.route("/api/email-config")
def email_config():
    from email_sender import load_config
    try:
        cfg = load_config()
        return jsonify({"default_recipients": cfg.get("default_recipients", [])})
    except Exception:
        return jsonify({"default_recipients": []})


@app.route("/api/send-email", methods=["POST"])
def send_email():
    from email_sender import send_html_only, load_config
    print("[send-email] Request received", flush=True)
    body = request.get_json()
    recipients = body.get("recipients", [])
    if not recipients:
        try:
            cfg = load_config()
            recipients = cfg.get("default_recipients", [])
        except Exception:
            return jsonify({"status": "error", "message": "No recipients and no config found"}), 400
    try:
        sent_to = send_html_only(recipients)
        print(f"[send-email] Success: {sent_to}", flush=True)
        return jsonify({"status": "ok", "sent_to": sent_to})
    except Exception as e:
        print(f"[send-email] Error: {e}", flush=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Fetch fresh data on startup if no cache
    if not load_cache():
        fetch_and_process()
    app.run(host="0.0.0.0", port=8082, debug=False)
