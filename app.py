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

@app.route("/api/reset-baseline", methods=["POST"])
def reset_baseline():
    """Force-reset today's baseline to the EOD (end-of-previous-day) snapshot."""
    import os, json
    from data_fetcher import EOD_CACHE_FILE, DAILY_BASELINE_FILE
    from datetime import datetime
    try:
        with open(EOD_CACHE_FILE) as f:
            eod = json.load(f)
        eod["baseline_date"] = datetime.now().strftime("%Y-%m-%d")
        with open(DAILY_BASELINE_FILE, "w") as f:
            json.dump(eod, f)
        return jsonify({"status": "ok", "message": "Baseline reset to end-of-previous-day snapshot"})
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "No EOD snapshot found — refresh will auto-create one at next midnight"}), 404


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
    from pdf_generator import build_pdf
    from email_sender import send_pdf, load_config
    body = request.get_json()
    recipients = body.get("recipients", [])
    if not recipients:
        try:
            cfg = load_config()
            recipients = cfg.get("default_recipients", [])
        except Exception:
            return jsonify({"status": "error", "message": "No recipients and no config found"}), 400
    try:
        from data_fetcher import DATA_DIR
        pdf_path = build_pdf(str(DATA_DIR / "management_summary.pdf"))
        sent_to = send_pdf(pdf_path, recipients)
        return jsonify({"status": "ok", "sent_to": sent_to})
    except FileNotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Fetch fresh data on startup if no cache
    if not load_cache():
        fetch_and_process()
    app.run(host="0.0.0.0", port=8082, debug=False)
