#!/usr/bin/env python3
"""
DSE Block Trade collector.

Fetches the Dhaka Stock Exchange "Market Statistics" page, parses the
"PRICES IN BLOCK TRANSACTIONS" table, and appends that trading day's rows to
data/blocktrades.json. It is date-idempotent: if the page's date is already
stored (e.g. it runs on a weekend/holiday when the page still shows the last
session), it makes no change. Intended to run once per day via GitHub Actions.
"""
import json, os, re, sys

URL = "https://www.dsebd.org/market-statistics.php"
DATA = os.path.join(os.path.dirname(__file__), "blocktrades.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DSEBlockTradeCollector/1.0)"}

ROW_RE = re.compile(r"^([A-Z0-9]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s*$")
DATE_RE = re.compile(r"BLOCK TRANSACTIONS\s*:\s*(\d{4}-\d{2}-\d{2})")


def fetch(url=URL):
    """GET the page. DSE serves an incomplete TLS chain, so fall back to an
    unverified request if verification fails — we only READ public data and
    transmit nothing sensitive."""
    import requests
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.exceptions.SSLError:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(url, headers=HEADERS, timeout=30, verify=False)
    r.raise_for_status()
    return r.text


def parse(text):
    """Return (date_str, [rows]) parsed from the block-transactions section."""
    m = DATE_RE.search(text)
    if not m:
        raise SystemExit("ERROR: block-transactions date not found — page format may have changed.")
    date = m.group(1)
    rows, in_section = [], False
    for line in text.splitlines():
        if "BLOCK TRANSACTIONS" in line:
            in_section = True
            continue
        if not in_section:
            continue
        s = line.strip()
        if s.startswith("---"):      # dashed totals separator ends the table
            break
        mm = ROW_RE.match(s)
        if mm:
            rows.append({
                "d": date, "t": mm.group(1),
                "mx": float(mm.group(2)), "mn": float(mm.group(3)),
                "tr": int(mm.group(4)), "q": int(mm.group(5)),
                "v": round(float(mm.group(6)), 3),
            })
    return date, rows


def load_db():
    if os.path.exists(DATA):
        with open(DATA) as f:
            return json.load(f)
    return {"updated": "", "rows": []}


def save_db(db):
    with open(DATA, "w") as f:
        json.dump(db, f, separators=(",", ":"))


def main():
    text = fetch()
    date, rows = parse(text)
    if not rows:
        raise SystemExit("ERROR: 0 block rows parsed — aborting without changes.")

    db = load_db()
    seen = {r["d"] for r in db["rows"]}
    if date in seen:
        print(f"No new trading day — {date} already stored ({len(rows)} rows on page). No change.")
        return

    db["rows"].extend(rows)
    db["updated"] = max(seen | {date})
    save_db(db)
    print(f"Appended {len(rows)} rows for {date}. Total rows now {len(db['rows'])}.")


if __name__ == "__main__":
    sys.exit(main())
