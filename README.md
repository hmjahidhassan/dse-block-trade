# DSE Block Trade Explorer

A free, self-updating website that lets anyone look up **block transactions** on the
Dhaka Stock Exchange by ticker and date range — showing a totals summary
(Max/Min price, No. of Trades, Quantity, Qty per Trade, Value, VWAP) and a
day-by-day table.

It runs entirely on GitHub at **$0/month**:

- **GitHub Pages** serves the website (`index.html`).
- **`blocktrades.json`** is the database — a plain JSON file the site reads.
- **GitHub Actions** runs `collector.py` once every trading day, appends the new
  day's block trades to the JSON, and commits it. Pages redeploys automatically.

Because the data lives in the repo, every update is version-controlled — your
history is inherently backed up in the commit log.

## Files

| File | Purpose |
|------|---------|
| `index.html` | The website (filters, KPI summary, day-by-day table). Pure HTML/JS, no build step. |
| `blocktrades.json` | Accumulating dataset (`{updated, rows:[{d,t,mx,mn,tr,q,v}]}`). |
| `collector.py` | Fetches DSE Market Statistics, parses the block table, appends new days (date-idempotent). |
| `.github/workflows/collect.yml` | Runs the collector daily at 17:00 Asia/Dhaka (5 PM) and commits changes. |
| `requirements.txt` | Python dependency (`requests`). |

## One-time deploy (checklist)

1. Create a **public** repo (e.g. `dse-block-trade`) and add these files.
2. **Settings → Pages** → *Build and deployment* → Source: **Deploy from a branch** →
   Branch: `main` / `/ (root)` → **Save**. Your link appears as
   `https://<username>.github.io/dse-block-trade/`.
3. **Settings → Actions → General → Workflow permissions** → select
   **Read and write permissions** → **Save** (lets the collector commit data).
4. **Actions** tab → *Collect DSE block trades* → **Run workflow** once, to confirm
   it can reach DSE and to fetch today's data. (This is where we verify the site
   is reachable from GitHub's servers.)
5. Share the Pages link.

## Run the collector locally (optional)

```bash
pip install -r requirements.txt
python collector.py        # appends today's block trades to blocktrades.json if new
```

## Notes

- **Schedule:** the workflow runs daily; the collector skips days already stored
  (weekends/holidays show the previous session, so nothing is duplicated).
- **Timezone:** GitHub cron is UTC. `0 11 * * *` = 17:00 Asia/Dhaka (5 PM). Adjust in
  `collect.yml` if you want a different time.
- **History** builds forward from launch — DSE publishes only the latest day, so
  earlier block-trade detail can't be back-filled.
- **Maintenance:** if DSE changes the page layout, the collector aborts without
  writing (and the Action shows a red X) rather than saving bad data — ping to fix
  the parser.
- **Source & terms:** data is DSE public market data (dsebd.org). Keep the "Source:
  DSE" attribution and the once-daily fetch cadence.
