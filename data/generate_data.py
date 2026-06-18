"""
Synthetic dataset generator for the Uganda / East Africa power grid dashboard.

IMPORTANT — data provenance:
This dataset is SIMULATED. Plant names, fuel mix, and approximate installed
capacities are loosely based on Uganda's real generation fleet (Nalubaale,
Kiira, Bujagali, Isimba, Karuma hydro stations; Namanve thermal; Tororo and
Soroti solar) to make the dashboard feel operationally realistic. Hourly
generation, demand, outage events, transmission losses, and reservoir water
levels are synthetically generated with seeded randomness and do NOT
represent actual UEGCL / UEDCL / ERA telemetry.

Run this once to (re)build the CSVs the dashboard reads from:
    python data/generate_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG_SEED = 42
rng = np.random.default_rng(RNG_SEED)

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(exist_ok=True)

START = pd.Timestamp("2025-01-01 00:00")
END = pd.Timestamp("2025-12-31 23:00")
HOURS = pd.date_range(START, END, freq="h")
N = len(HOURS)

# ---------------------------------------------------------------------------
# Fleet definition: name, source type, installed capacity (MW), baseline
# capacity factor, commissioning year (older units -> more outages later)
# ---------------------------------------------------------------------------
PLANTS = [
    ("Nalubaale", "Hydro", 180, 0.70, 1954),
    ("Kiira", "Hydro", 200, 0.72, 2000),
    ("Bujagali", "Hydro", 250, 0.78, 2012),
    ("Isimba", "Hydro", 183, 0.80, 2019),
    ("Karuma", "Hydro", 600, 0.82, 2023),
    ("Tororo Solar", "Solar", 10, 0.20, 2016),
    ("Soroti Solar", "Solar", 10, 0.20, 2017),
    ("Namanve Thermal", "Thermal", 50, 0.12, 2009),
]
PLANT_NAMES = [p[0] for p in PLANTS]

# Region: name, demand share of national total, base T&D loss %, lat, lon
REGIONS = [
    ("Kampala Metro", 0.45, 0.09, 0.3476, 32.5825),
    ("Central", 0.20, 0.11, 0.7167, 31.7833),
    ("Eastern", 0.15, 0.14, 1.1500, 33.7833),
    ("Northern", 0.10, 0.18, 2.7747, 32.2990),
    ("Western", 0.10, 0.15, 0.6000, 30.2500),
]

# ---------------------------------------------------------------------------
# 1. Reservoir / Lake Victoria-Nile water level index (daily, 15-95 scale)
#    Two rainy-season bumps + a mid-year drought dip for narrative drama.
# ---------------------------------------------------------------------------
days = pd.date_range(START, END, freq="D")
nd = len(days)
t = np.arange(nd)
seasonal = 8 * np.sin(2 * np.pi * (t - 60) / 365) + 4 * np.sin(4 * np.pi * (t - 30) / 365)
drought = -14 * np.exp(-((t - 195) ** 2) / (2 * 32 ** 2))  # dip around mid-July
drift = rng.normal(0, 1.0, nd).cumsum() * 0.04
water_level = np.clip(65 + seasonal + drought + drift, 15, 95)

water_df = pd.DataFrame({"date": days, "water_level_index": water_level.round(2)})
water_df.to_csv(OUT_DIR / "water_levels.csv", index=False)

# Map daily level -> hourly hydro modulation factor (0.65 - 1.05)
water_by_day = dict(zip(days, water_level))
water_hourly = np.array([water_by_day[h.normalize()] for h in HOURS])
hydro_water_factor = 0.65 + (water_hourly - 15) / (95 - 15) * 0.40

# ---------------------------------------------------------------------------
# 2. Demand shape: hour-of-day curve typical of an East African urban+rural
#    grid (morning ramp, midday plateau, evening peak), weekday/weekend,
#    and a gentle annual growth trend.
# ---------------------------------------------------------------------------
HOUR_SHAPE = {
    0: 0.58, 1: 0.55, 2: 0.52, 3: 0.50, 4: 0.52, 5: 0.58, 6: 0.68, 7: 0.82,
    8: 0.92, 9: 0.88, 10: 0.82, 11: 0.80, 12: 0.80, 13: 0.78, 14: 0.76,
    15: 0.75, 16: 0.78, 17: 0.85, 18: 0.95, 19: 1.00, 20: 0.97, 21: 0.90,
    22: 0.78, 23: 0.66,
}
hour_of_day = HOURS.hour
shape_arr = np.array([HOUR_SHAPE[h] for h in hour_of_day])
is_weekend = HOURS.weekday >= 5
weekend_factor = np.where(is_weekend, 0.92, 1.0)

day_index = (HOURS - START).days.values
growth = 880 + (950 - 880) * (day_index / day_index.max())  # MW peak base, Jan->Dec
demand_noise = rng.normal(0, 0.025, N)
national_demand = growth * shape_arr * weekend_factor * (1 + demand_noise)

# ---------------------------------------------------------------------------
# 3. Outage events (per plant): Poisson count, random start, exponential-ish
#    duration, cause depends on plant type and age.
# ---------------------------------------------------------------------------
OUTAGE_LAMBDA = {
    "Nalubaale": 6, "Kiira": 5, "Bujagali": 4, "Isimba": 3, "Karuma": 2,
    "Tororo Solar": 3, "Soroti Solar": 3, "Namanve Thermal": 10,
}
HYDRO_CAUSES = ["Scheduled Maintenance", "Forced Outage - Mechanical",
                "Forced Outage - Electrical", "Grid Fault"]
SOLAR_CAUSES = ["Scheduled Maintenance", "Inverter Fault", "Grid Fault",
                "Weather Curtailment"]
THERMAL_CAUSES = ["Scheduled Maintenance", "Forced Outage - Mechanical",
                   "Fuel Supply Issue", "Grid Fault"]

outage_rows = []
plant_outage_mask = {name: np.zeros(N, dtype=bool) for name in PLANT_NAMES}

for name, source, capacity, base_cf, year in PLANTS:
    n_events = rng.poisson(OUTAGE_LAMBDA[name])
    causes = HYDRO_CAUSES if source == "Hydro" else SOLAR_CAUSES if source == "Solar" else THERMAL_CAUSES
    for _ in range(n_events):
        start_h = rng.integers(0, N - 1)
        duration = int(np.clip(rng.exponential(18), 2, 120))
        end_h = min(start_h + duration, N - 1)
        cause = rng.choice(causes, p=[0.35, 0.30, 0.20, 0.15] if len(causes) == 4 else None)
        outage_rows.append({
            "plant": name,
            "source": source,
            "start_time": HOURS[start_h],
            "end_time": HOURS[end_h],
            "duration_hrs": end_h - start_h + 1,
            "cause": cause,
            "mw_lost": capacity,
        })
        plant_outage_mask[name][start_h:end_h + 1] = True

outage_df = pd.DataFrame(outage_rows).sort_values("start_time").reset_index(drop=True)
outage_df.to_csv(OUT_DIR / "outage_events.csv", index=False)

# ---------------------------------------------------------------------------
# 4. Hourly generation per plant
# ---------------------------------------------------------------------------
solar_hour_shape = np.clip(np.sin(np.pi * (hour_of_day - 6) / 12), 0, None)
solar_hour_shape = np.where((hour_of_day >= 6) & (hour_of_day <= 18), solar_hour_shape, 0)
cloud_noise = rng.normal(1.0, 0.08, N)

gen_frames = []
hydro_total = np.zeros(N)
solar_total = np.zeros(N)

for name, source, capacity, base_cf, year in PLANTS:
    online = ~plant_outage_mask[name]
    if source == "Hydro":
        noise = rng.normal(1.0, 0.04, N)
        output = capacity * base_cf * hydro_water_factor * noise
        output = np.clip(output, 0, capacity)
        hydro_total += np.where(online, output, 0)
        output = np.where(online, output, 0)
    elif source == "Solar":
        output = capacity * 0.85 * solar_hour_shape * cloud_noise
        output = np.clip(output, 0, capacity)
        solar_total += np.where(online, output, 0)
        output = np.where(online, output, 0)
    else:  # Thermal — dispatched later as the gap-filler; placeholder for now
        output = np.zeros(N)

    gen_frames.append(pd.DataFrame({
        "timestamp": HOURS, "plant": name, "source": source,
        "capacity_mw": capacity, "output_mw": np.round(output, 2),
        "status": np.where(online, "Online", "Outage"),
    }))

# Thermal: merit-order dispatch to fill the gap between demand+losses and
# hydro+solar supply, capped at its own capacity and respecting its outages.
avg_loss_pct = sum(r[1] * r[2] for r in REGIONS)  # demand-weighted average loss
demand_with_losses = national_demand * (1 + avg_loss_pct)
renewable_supply = hydro_total + solar_total
thermal_capacity, _, _, _, _ = [p for p in PLANTS if p[1] == "Thermal"][0][2], None, None, None, None
thermal_name = "Namanve Thermal"
thermal_cap = 50
thermal_online = ~plant_outage_mask[thermal_name]
deficit = np.clip(demand_with_losses - renewable_supply, 0, None)
thermal_output = np.clip(deficit, 0, thermal_cap) * thermal_online
thermal_output = thermal_output * rng.normal(1.0, 0.03, N)
thermal_output = np.clip(thermal_output, 0, thermal_cap)

for frame in gen_frames:
    if (frame["plant"] == thermal_name).all():
        frame["output_mw"] = np.round(thermal_output, 2)
        frame["status"] = np.where(thermal_online, "Online", "Outage")

generation_df = pd.concat(gen_frames, ignore_index=True)
generation_df.to_csv(OUT_DIR / "generation_hourly.csv", index=False)

# ---------------------------------------------------------------------------
# 5. National frequency + total supply/deficit
# ---------------------------------------------------------------------------
total_supply = renewable_supply + thermal_output
unmet = np.clip(demand_with_losses - total_supply, 0, None)
frequency = 50.0 - (unmet / 60) * 0.6 + rng.normal(0, 0.025, N)
frequency = np.clip(frequency, 48.6, 50.3)

national_df = pd.DataFrame({
    "timestamp": HOURS,
    "demand_mw": np.round(national_demand, 2),
    "demand_with_losses_mw": np.round(demand_with_losses, 2),
    "hydro_supply_mw": np.round(hydro_total, 2),
    "solar_supply_mw": np.round(solar_total, 2),
    "thermal_supply_mw": np.round(thermal_output, 2),
    "total_supply_mw": np.round(total_supply, 2),
    "unmet_demand_mw": np.round(unmet, 2),
    "frequency_hz": np.round(frequency, 3),
})
national_df.to_csv(OUT_DIR / "national_summary.csv", index=False)

# ---------------------------------------------------------------------------
# 6. Regional demand + transmission losses
# ---------------------------------------------------------------------------
reg_frames = []
for name, share, base_loss, lat, lon in REGIONS:
    reg_noise = rng.normal(1.0, 0.03, N)
    reg_demand = national_demand * share * reg_noise
    loss_seasonal = 0.02 * np.sin(2 * np.pi * (day_index - 60) / 365)
    loss_noise = rng.normal(0, 0.01, N)
    loss_pct = np.clip(base_loss + loss_seasonal + loss_noise, 0.04, 0.28)
    reg_frames.append(pd.DataFrame({
        "timestamp": HOURS, "region": name, "lat": lat, "lon": lon,
        "demand_mw": np.round(reg_demand, 2),
        "transmission_loss_pct": np.round(loss_pct * 100, 2),
        "frequency_hz": np.round(frequency, 3),
    }))

regional_df = pd.concat(reg_frames, ignore_index=True)
regional_df.to_csv(OUT_DIR / "regional_load.csv", index=False)

print("Generated files in", OUT_DIR)
print(" - national_summary.csv  ", national_df.shape)
print(" - generation_hourly.csv ", generation_df.shape)
print(" - regional_load.csv     ", regional_df.shape)
print(" - outage_events.csv     ", outage_df.shape)
print(" - water_levels.csv      ", water_df.shape)
