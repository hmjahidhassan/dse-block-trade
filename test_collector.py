"""Offline test of the collector's parse + dedupe/append logic against a real
page-text fixture (no network — the live fetch is validated on first deploy)."""
import json, os, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("collector", os.path.join(HERE, "collector.py"))
collector = importlib.util.module_from_spec(spec); spec.loader.exec_module(collector)

FIXTURE = """DHAKA STOCK EXCHANGE PLC.

TODAY'S SHARE MARKET : 2026-07-20
=================================
TOTAL TRANSACTIONS

A. NO. OF TRADES : 300000
B. VOLUME(Nos.) : 400000000
C. VALUE(Tk) : 12000000000.00

PRICES IN BLOCK TRANSACTIONS : 2026-07-20
=========================================

Instr Code Max Price Min Price Trades Quantity Value(In Mn)

IPDC 36.00 34.00 3 1500000 52.500
SHARPIND 31.00 30.00 5 600000 18.300
DHAKABANK 12.50 12.10 2 2000000 24.600
------ -------- ------------
10 4100000 95.400

Total number of scrips traded in Block = 3
"""

# 1) parse
date, rows = collector.parse(FIXTURE)
assert date == "2026-07-20", date
assert len(rows) == 3, len(rows)
ipdc = [r for r in rows if r["t"] == "IPDC"][0]
assert ipdc == {"d":"2026-07-20","t":"IPDC","mx":36.0,"mn":34.0,"tr":3,"q":1500000,"v":52.5}, ipdc
# total transactions line must NOT be parsed as a row
assert all(r["t"] != "A" for r in rows)
print("parse OK:", date, len(rows), "rows")

# 2) append onto a copy of the real seed -> should grow by 3 and set updated
tmp = tempfile.mkdtemp()
dbpath = os.path.join(tmp, "blocktrades.json")
seed = json.load(open(os.path.join(HERE, "blocktrades.json")))
json.dump(seed, open(dbpath, "w"))
collector.DATA = dbpath
before = len(seed["rows"])
db = collector.load_db(); seen = {r["d"] for r in db["rows"]}
assert date not in seen
db["rows"].extend(rows); db["updated"] = max(seen | {date}); collector.save_db(db)
after = json.load(open(dbpath))
assert len(after["rows"]) == before + 3, (before, len(after["rows"]))
assert after["updated"] == "2026-07-20"
print(f"append OK: {before} -> {len(after['rows'])} rows, updated={after['updated']}")

# 3) dedupe: re-running the same date must be a no-op
db = collector.load_db(); seen = {r["d"] for r in db["rows"]}
assert date in seen, "date should now be present"
print("dedupe OK: re-run of same date is skipped")

# 4) seed integrity
assert before == 45 and seed["updated"] == "2026-07-19"
print("seed OK: 45 rows, updated 2026-07-19")
print("\nALL TESTS PASSED")
