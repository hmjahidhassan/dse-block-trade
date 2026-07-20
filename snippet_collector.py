#!/usr/bin/env python3
"""
DSE Daily Market Snippet collector — client-type Buy%/Sell%.

Downloads the DSE "Daily Market Snippet" PDF, reads the CLIENT TYPE WISE
STATISTICS table (Retail, Institution, Dealer, Foreign, Others — Buy % and
Sale %), and appends that day's row to client_stats.json. Date-idempotent:
if the snippet's date is already stored, it makes no change. Runs daily.
"""
import datetime, io, json, os, re, sys

URL = "https://www.dsebd.org/assets/pdf/dse-daily-market-snippet.pdf"
DATA = os.path.join(os.path.dirname(__file__), "client_stats.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DSESnippetCollector/1.0)"}

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}
# (label in PDF, json key prefix)
TYPES = [("Retail", "retail"), ("Institution", "inst"), ("Dealer", "dealer"),
         ("Foreign", "foreign"), ("Others", "others")]


def fetch(url=URL):
    """Download the PDF bytes. DSE serves an incomplete TLS chain, so fall back
    to an unverified request (we only READ public data)."""
    import requests
    try:
        r = requests.get(url, headers=HEADERS, timeout=40)
    except requests.exceptions.SSLError:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(url, headers=HEADERS, timeout=40, verify=False)
    r.raise_for_status()
    return r.content


def extract_text(pdf_bytes):
    import pdfplumber
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            out.append(page.extract_text() or "")
    return "\n".join(out)


def parse(text):
    """Return (date_iso, row_dict) from the snippet text."""
    m = re.search(r"(January|February|March|April|May|June|July|August|"
                  r"September|October|November|December)\s+(\d{1,2}),\s+(\d{4})", text)
    if not m:
        raise SystemExit("ERROR: snippet date not found — PDF format may have changed.")
    date = datetime.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).isoformat()

    row = {"d": date}
    for label, key in TYPES:
        # LABEL  Buy%  Sale%  (%ofTotal) — capture the first two percentages
        mm = re.search(label + r"\s+([\d.]+)\s*%\s+([\d.]+)\s*%", text)
        if not mm:
            raise SystemExit(f"ERROR: client type '{label}' not found — PDF format may have changed.")
        row[key + "_b"] = float(mm.group(1))
        row[key + "_s"] = float(mm.group(2))
    return date, row


def load_db():
    if os.path.exists(DATA):
        with open(DATA) as f:
            return json.load(f)
    return {"updated": "", "rows": []}


def save_db(db):
    with open(DATA, "w") as f:
        json.dump(db, f, separators=(",", ":"))


def main():
    date, row = parse(extract_text(fetch()))
    db = load_db()
    seen = {r["d"] for r in db["rows"]}
    if date in seen:
        print(f"No new snippet — {date} already stored. No change.")
        return
    db["rows"].append(row)
    db["updated"] = max(seen | {date})
    save_db(db)
    print(f"Appended client-type stats for {date}. Total rows now {len(db['rows'])}.")


if __name__ == "__main__":
    sys.exit(main())
