# Uganda Power Grid Operations Dashboard

A production-grade, multi-page interactive dashboard built with **Python 3.12, Pandas, Plotly, and Dash**, served by **Gunicorn** and deployed on **Render**.

Live demo: _add your Render URL here after deploying_

---

## What it is

Industrial and operational data dies in spreadsheets. This dashboard takes a simulated year of hourly Uganda national grid data — generation by plant, regional demand, transmission losses, grid frequency, reservoir water levels, and outage events — and turns it into three cross-filtered operational views:

1. **National Overview** (`/`) — KPI cards, stacked generation-mix-vs-demand area chart, energy mix donut, and grid frequency stability chart, all responsive to a date-range picker.
2. **Regional Drill-down** (`/regional`) — click a region on the map to drill into its hourly load curve, transmission-loss trend, and the outages that affected national supply in that window.
3. **Plant Performance & Maintenance** (`/plants`) — capacity factor ranking across the fleet, a Gantt-style outage timeline, and a dual-axis chart correlating hydro output with reservoir water levels (the drought story).

## Data provenance — read this before judging

**The dataset is simulated.** Plant names and approximate installed capacities (Nalubaale, Kiira, Bujagali, Isimba, Karuma hydro stations; Namanve thermal peaker; Tororo and Soroti solar) are based on Uganda's real generation fleet to make the dashboard operationally credible. Hourly generation, demand, transmission losses, outage events, and reservoir water levels are synthetically generated with a fixed random seed (`data/generate_data.py`) and do **not** represent actual UEGCL / UEDCL / ERA telemetry. This satisfies the hackathon's "simulate one that tells a real operational story" option.

The simulation models real grid dynamics: a daily two-peak load curve, weekday/weekend variation, a mid-year drought that drags down hydro output and forces merit-order thermal dispatch, regional transmission losses that scale with rurality, and Poisson-distributed outage events weighted by plant age and source type.

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Data processing | Pandas, NumPy |
| Visualization / UI | Plotly, Dash (multi-page, `dash.register_page`) |
| Styling | Dash Bootstrap Components (Cyborg theme) |
| WSGI server | Gunicorn |
| Hosting | Render (free tier) |

## Project structure

```
power-grid-dashboard/
  app.py                  → Dash app entry point, exposes `server` for Gunicorn
  data_loader.py           → loads CSVs once, shared across pages
  data/
    generate_data.py       → synthetic dataset generator (run once)
    national_summary.csv   → hourly national demand/supply/frequency
    generation_hourly.csv  → hourly output per plant
    regional_load.csv      → hourly demand/loss per region
    outage_events.csv      → outage log per plant
    water_levels.csv       → daily reservoir water level index
  pages/
    overview.py             → National Overview page + callbacks
    regional.py             → Regional Drill-down page + callbacks
    plants.py                → Plant Performance page + callbacks
  requirements.txt
  Procfile                  → Gunicorn start command (Heroku-style, also read by Render)
  render.yaml               → Render Blueprint (optional one-click deploy)
```

## Run locally (under 5 minutes)

```bash
git clone <this-repo-url>
cd power-grid-dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python data/generate_data.py     # regenerates the CSVs (already committed, but reproducible)
python app.py                    # dev server at http://localhost:8050
```

To run it exactly the way it runs in production:

```bash
gunicorn app:server --bind 0.0.0.0:8050 --workers 2 --timeout 120
```

## Deploy to Render (free tier)

1. Push this repo to GitHub.
2. On [render.com](https://render.com), click **New > Web Service** and connect the repo (Render auto-detects `render.yaml`, or set it up manually with the values below).
3. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
4. Deploy. Render assigns a live `*.onrender.com` URL — that's your submission link.

Note: Render's free tier spins down on inactivity and takes 30-60s to wake on the first request after idling — worth mentioning to judges if they hit a cold start.

## Required write-up (~200 words)

**What the dataset represents:** A simulated full year (8,760 hours) of Uganda's national power grid operations — generation from five hydro stations, two solar plants, and one thermal peaker, demand and transmission losses across five regions, plus outage events and reservoir water levels. Plant identities and capacities are grounded in Uganda's real fleet; the time series itself is synthetic.

**What story the dashboard tells:** A mid-year drought drags down hydro output, forcing the thermal peaker into heavier merit-order dispatch and pushing grid frequency away from the 50 Hz nominal during the worst hours — visible by switching to the Plant Performance page and watching the water-level/output correlation diverge in July. The Regional page shows that rural northern and western regions carry both lower demand and the highest transmission losses, the opposite of what a naive "biggest region = biggest problem" assumption would suggest.

**Hardest part in Dash:** Getting cross-filtering right without page reloads — using a `dcc.Store` to hold the clicked region so a Scattermap click event on one chart correctly triggers three independent downstream callbacks (load curve, loss trend, outage table) while keeping the date-range picker as a second, independent input to all of them.

---
*Built for the Kolaborate "Build the Dashboard" Python Data Visualisation Sprint, June 2026.*
