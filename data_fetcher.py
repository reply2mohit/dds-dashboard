import csv
import json
import io
import os
import requests
from datetime import datetime
from pathlib import Path

SHEET_ID = "1gQKYzhkb7j6iXqmLrDZTeXxR_2RZ5O8TaydpibK9iug"
SHEET_NAME = "Sheet to be used"
# gviz endpoint lets us specify sheet by name; works on publicly shared sheets
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME.replace(' ', '%20')}"

DATA_DIR = Path(os.environ.get("DATA_DIR", "."))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE              = str(DATA_DIR / "cache.json")
PREV_CACHE_FILE         = str(DATA_DIR / "cache_prev.json")
DAILY_BASELINE_FILE     = str(DATA_DIR / "cache_baseline.json")
EOD_CACHE_FILE          = str(DATA_DIR / "cache_eod.json")
FORCED_COMPLETIONS_FILE = str(DATA_DIR / "forced_completions.json")

MARKETPLACES = [
    "amazon link", "Walmart Link", "Kohls Link", "Target Link",
    "TEMU Link", "Zulily Link", "Ebay Link", "Ebay LOTS Link",
    "Sears Link", "TikTok Link", "Debenhams Link", "D2c Link",
    "Wayfair Link", "mercado libre Link"
]

MARKETPLACE_DISPLAY = {
    "amazon link": "Amazon",
    "Walmart Link": "Walmart",
    "Kohls Link": "Kohls",
    "Target Link": "Target",
    "TEMU Link": "TEMU",
    "Zulily Link": "Zulily",
    "Ebay Link": "eBay",
    "Ebay LOTS Link": "eBay LOTS",
    "Sears Link": "Sears",
    "TikTok Link": "TikTok",
    "Debenhams Link": "Debenhams",
    "D2c Link": "D2C",
    "Wayfair Link": "Wayfair",
    "mercado libre Link": "Mercado Libre"
}

SKIP_BRANDS = {"Brand Name", "NO_HEADER", "NO\\_HEADER", "SKU", "DDS Status", ""}


_NEGATIVE = {"", "n/a", "#n/a", "no", "none", "not started", "not live", "-", "—", "na"}

def is_live_url(val):
    """Any non-empty, non-negative value counts as live on that marketplace."""
    v = val.strip()
    return bool(v and v.lower() not in _NEGATIVE)


def classify_status(raw):
    s = raw.lower().strip()
    if not s or s.startswith("http"):
        return "not_started"
    elif "pending" in s:
        return "pending"
    else:
        return "completed"


def is_valid_brand(brand):
    b = brand.strip()
    if b in SKIP_BRANDS:
        return False
    if b.startswith("http") or b.startswith("https"):
        return False
    return True


def compute_changes(prev, curr):
    """
    Diff two snapshots and return a changes dict with:
    - new_skus:        SKUs added since last snapshot
    - dds_completed:   SKUs whose DDS status became 'completed'
    - mp_gained:       SKUs that gained new marketplace links
    - summary:         brand-level summary of each change type
    """
    if not prev:
        return None

    # Detect old cache format (no live_marketplaces per SKU) — skip MP diff
    sample_skus = [s for b in prev.get("brands", []) for s in b.get("skus", [])]
    old_format = sample_skus and "live_marketplaces" not in sample_skus[0]

    # Build flat SKU maps keyed by (brand, asin, sku)
    def sku_map(data):
        m = {}
        for b in data.get("brands", []):
            for s in b.get("skus", []):
                key = (b["name"], s["asin"], s["sku"])
                m[key] = s
        return m

    prev_map = sku_map(prev)
    curr_map = sku_map(curr)

    new_skus       = []
    dds_completed  = []
    mp_gained      = []

    for key, curr_sku in curr_map.items():
        brand, asin, sku = key
        if key not in prev_map:
            new_skus.append({"brand": brand, "asin": asin, "sku": sku, "status": curr_sku["status"]})
        else:
            prev_sku = prev_map[key]
            # DDS status upgrade to completed
            if prev_sku["status"] != "completed" and curr_sku["status"] == "completed":
                dds_completed.append({"brand": brand, "asin": asin, "sku": sku})
            # Marketplace gains (skip if old cache format)
            if not old_format:
                prev_mp = prev_sku.get("live_marketplaces", [])
                curr_mp = curr_sku.get("live_marketplaces", [])
                gained = [mp for mp in curr_mp if mp not in prev_mp]
                if gained:
                    mp_gained.append({"brand": brand, "asin": asin, "sku": sku, "gained": gained})

    # Brand-level summary
    def group_by_brand(items):
        out = {}
        for item in items:
            b = item["brand"]
            out.setdefault(b, []).append(item)
        return out

    baseline_date = prev.get("last_updated", prev.get("baseline_date", ""))
    since_label = baseline_date[:10] if len(str(baseline_date)) >= 10 else "previous day"
    return {
        "since": since_label,
        "new_skus":       new_skus,
        "dds_completed":  dds_completed,
        "mp_gained":      mp_gained,
        "new_skus_by_brand":      group_by_brand(new_skus),
        "dds_completed_by_brand": group_by_brand(dds_completed),
        "mp_gained_by_brand":     group_by_brand(mp_gained),
        "total_new_skus":      len(new_skus),
        "total_dds_completed": len(dds_completed),
        "total_mp_gained":     len(mp_gained),
    }


def fetch_and_process():
    resp = requests.get(CSV_URL, timeout=30)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)

    normalized_rows = []
    for row in rows:
        normalized_rows.append({k.strip(): v.strip() for k, v in row.items()})

    brands = {}

    for row in normalized_rows:
        brand = row.get("Brand Name", "").strip()
        if not is_valid_brand(brand):
            continue

        dds_status_raw = row.get("DDS Status", "")
        status = classify_status(dds_status_raw)

        live_marketplaces = []
        for mp in MARKETPLACES:
            val = row.get(mp, "")
            if is_live_url(val):
                live_marketplaces.append(MARKETPLACE_DISPLAY[mp])

        if brand not in brands:
            brands[brand] = {
                "name": brand,
                "total": 0,
                "completed": 0,
                "pending": 0,
                "not_started": 0,
                "mp_counts": {mp: 0 for mp in MARKETPLACES},
                "skus": []
            }

        brands[brand]["total"] += 1
        brands[brand][status] += 1
        for mp in MARKETPLACES:
            val = row.get(mp, "")
            if is_live_url(val):
                brands[brand]["mp_counts"][mp] += 1

        brands[brand]["skus"].append({
            "asin": row.get("ASIN", ""),
            "sku": row.get("SKU Code", ""),
            "status": status,
            "live_on": len(live_marketplaces),
            "live_marketplaces": live_marketplaces   # store per-SKU for diffing
        })

    result = []
    for brand_data in brands.values():
        total     = brand_data["total"]
        completed = brand_data["completed"]
        pct       = round((completed / total) * 100) if total > 0 else 0

        mp_sku_counts = {
            MARKETPLACE_DISPLAY[mp]: brand_data["mp_counts"][mp]
            for mp in MARKETPLACES
        }
        live_mp_display = [MARKETPLACE_DISPLAY[mp] for mp in MARKETPLACES if brand_data["mp_counts"][mp] > 0]

        result.append({
            "name": brand_data["name"],
            "total": total,
            "completed": completed,
            "pending": brand_data["pending"],
            "not_started": brand_data["not_started"],
            "pct_complete": pct,
            "live_marketplaces": sorted(live_mp_display),
            "marketplace_count": len(live_mp_display),
            "mp_sku_counts": mp_sku_counts,
            "skus": brand_data["skus"]
        })

    result.sort(key=lambda x: x["name"].lower())

    all_mp_names = [MARKETPLACE_DISPLAY[mp] for mp in MARKETPLACES]
    mp_totals = {
        mp_name: sum(b["mp_sku_counts"].get(mp_name, 0) for b in result)
        for mp_name in all_mp_names
    }

    # Changes = yesterday vs today (calendar date, not rolling 24h).
    # cache_eod.json always holds the last save from the PREVIOUS calendar day.
    # cache_baseline.json is today's active baseline — set once per day and
    # never overwritten during the day so all refreshes accumulate correctly.
    today = datetime.now().strftime("%Y-%m-%d")

    # Step 1: Before overwriting cache.json, check if it belongs to a previous date.
    #         If so, persist it as the EOD snapshot for that date.
    existing_cache = load_cache()
    if existing_cache:
        cache_date = existing_cache.get("last_updated", "")[:10]
        if cache_date and cache_date != today:
            with open(EOD_CACHE_FILE, "w") as f:
                json.dump(existing_cache, f)

    # Step 2: On the first refresh of a new calendar day, promote the EOD snapshot
    #         to the active baseline.  Never update it again until tomorrow.
    baseline = _load_daily_baseline()
    if baseline is None or baseline.get("baseline_date") != today:
        eod = _load_eod_cache()
        src = eod if eod else existing_cache   # fallback for first-ever run
        if src:
            src = dict(src)
            src["baseline_date"] = today
            with open(DAILY_BASELINE_FILE, "w") as f:
                json.dump(src, f)
            baseline = src

    changes = compute_changes(baseline, {"brands": result})

    # Auto-heal: sheet never gets more than ~20 new SKUs in a day.
    # If >50 appear "new", the baseline is stale — reset silently.
    if changes and changes["total_new_skus"] > 50:
        print(f"[baseline] Stale baseline detected ({changes['total_new_skus']} SKUs flagged new, expected ≤20) — auto-resetting", flush=True)
        fresh_baseline = {"brands": result, "baseline_date": today,
                          "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        with open(DAILY_BASELINE_FILE, "w") as f:
            json.dump(fresh_baseline, f)
        changes = None

    changes = _merge_forced_completions(changes, result, today)

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_skus": sum(b["total"] for b in result),
        "total_completed": sum(b["completed"] for b in result),
        "total_pending": sum(b["pending"] for b in result),
        "total_not_started": sum(b["not_started"] for b in result),
        "all_marketplaces": all_mp_names,
        "mp_totals": mp_totals,
        "brands": result,
        "changes": changes
    }

    with open(CACHE_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[{output['last_updated']}] Fetched {output['total_skus']} SKUs across {len(result)} brands.")
    if changes:
        print(f"  Changes: {changes['total_new_skus']} new SKUs, "
              f"{changes['total_dds_completed']} DDS completed, "
              f"{changes['total_mp_gained']} gained new MPs")
    return output


def load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _load_daily_baseline():
    try:
        with open(DAILY_BASELINE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _load_eod_cache():
    try:
        with open(EOD_CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_forced_completions():
    try:
        with open(FORCED_COMPLETIONS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_forced_completions(asins, today):
    existing = load_forced_completions()
    if existing and existing.get("date") == today:
        merged = list(set(existing.get("asins", []) + asins))
    else:
        merged = list(set(asins))
    with open(FORCED_COMPLETIONS_FILE, "w") as f:
        json.dump({"date": today, "asins": merged}, f)
    return merged


def _merge_forced_completions(changes, result, today):
    forced = load_forced_completions()
    if not forced or forced.get("date") != today or not forced.get("asins"):
        return changes

    forced_set = set(forced["asins"])

    # Build ASIN → {brand, sku, asin} from current data
    asin_map = {}
    for brand in result:
        for sku in brand["skus"]:
            if sku["asin"] in forced_set:
                asin_map[sku["asin"]] = {"brand": brand["name"], "sku": sku["sku"], "asin": sku["asin"]}

    if not asin_map:
        return changes

    if changes is None:
        changes = {
            "since": today,
            "new_skus": [], "dds_completed": [], "mp_gained": [],
            "new_skus_by_brand": {}, "dds_completed_by_brand": {}, "mp_gained_by_brand": {},
            "total_new_skus": 0, "total_dds_completed": 0, "total_mp_gained": 0,
        }

    existing_asins = {item["asin"] for item in changes["dds_completed"]}
    for asin, item in asin_map.items():
        if asin not in existing_asins:
            changes["dds_completed"].append(item)

    changes["total_dds_completed"] = len(changes["dds_completed"])
    by_brand = {}
    for item in changes["dds_completed"]:
        by_brand.setdefault(item["brand"], []).append(item)
    changes["dds_completed_by_brand"] = by_brand

    return changes


if __name__ == "__main__":
    fetch_and_process()
